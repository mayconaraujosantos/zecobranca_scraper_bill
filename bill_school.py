import json
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class PixScraperBill:
    pass


class PixScraperEducAdventista:
    def __init__(self, headless: bool = True):
        self.session = requests.Session()
        self.base_url = "https://7edu-br.educadventista.org"
        self.login_url = f"{self.base_url}/studentportal/externalpayment/Login"
        self.payment_url = f"{self.base_url}/studentportal/externalpayment"

        # Configurar driver do Selenium
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.quit()

    def login(self, cpf: str, birth_date: str) -> bool:
        """
        Realiza o login no sistema
        """
        try:
            print(f"Fazendo login com CPF: {cpf}")

            # Navegar para página de login
            self.driver.get(self.payment_url)
            time.sleep(2)

            # Preencher CPF
            cpf_input = self.wait.until(
                EC.presence_of_element_located((By.NAME, "cpf"))
            )
            cpf_input.clear()
            cpf_input.send_keys(cpf)

            # Preencher data de nascimento
            birth_input = self.driver.find_element(By.NAME, "birthDate")
            birth_input.clear()
            birth_input.send_keys(birth_date)

            # Clicar no botão de login
            login_button = self.driver.find_element(
                By.CSS_SELECTOR, "button[type='submit'], input[type='submit']"
            )
            login_button.click()

            # Aguardar redirecionamento
            time.sleep(3)

            # Verificar se login foi bem-sucedido
            current_url = self.driver.current_url
            if "externalpayment" in current_url and "Login" not in current_url:
                print("Login realizado com sucesso!")
                return True
            else:
                print("Erro no login - verificar credenciais")
                return False

        except Exception as e:
            print(f"Erro durante o login: {str(e)}")
            return False

    def navigate_to_payment(self, target_date: str = None) -> bool:
        """
        Navega até a página de pagamento e clica nos botões necessários
        """
        try:
            print("Navegando para página de pagamento...")

            # Aguardar carregamento da página
            time.sleep(2)

            # 1. Clicar no botão de Parcelas
            print("Procurando botão de Parcelas...")
            parcelas_selectors = [
                "div.student-button.installments-button",
                "div.installments-button",
                "div[class*='installments']",
                "//div[contains(@class, 'installments-button')]",
                "//p[contains(text(), 'Parcelas')]",
                "//div[contains(text(), 'Parcelas')]",
            ]

            parcelas_button = None
            for selector in parcelas_selectors:
                try:
                    if selector.startswith("//"):
                        parcelas_button = self.driver.find_element(By.XPATH, selector)
                    else:
                        parcelas_button = self.driver.find_element(
                            By.CSS_SELECTOR, selector
                        )

                    if parcelas_button and parcelas_button.is_displayed():
                        break
                except:
                    continue

            if not parcelas_button:
                print("❌ Botão de Parcelas não encontrado")
                return False

            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", parcelas_button
            )
            time.sleep(1)
            self.driver.execute_script("arguments[0].click();", parcelas_button)
            print("✅ Clicou no botão de Parcelas")
            time.sleep(3)

            # 2. Selecionar parcela específica se target_date for fornecido
            if target_date:
                print(f"🔍 Buscando parcela com vencimento: {target_date}")
                if not self._select_specific_installment(target_date):
                    print(
                        "❌ Não foi possível selecionar a parcela específica, usando primeira disponível"
                    )
                    # Fallback para primeira parcela
                    if not self._click_first_pay_button():
                        return False
            else:
                # Clicar no primeiro botão Pagar
                if not self._click_first_pay_button():
                    return False

            # 3. Clicar no botão "Ir para pagamento"
            if not self._click_go_to_payment_button():
                return False

            return True

        except Exception as e:
            print(f"❌ Erro ao navegar para pagamento: {str(e)}")
            return False

    def _normalize_date(self, date_str: str) -> str:
        """
        Normaliza a data para comparação
        """
        # Remover espaços e converter para minúsculas
        normalized = date_str.lower().strip()

        # Mapear meses em português para números
        month_mapping = {
            "janeiro": "01",
            "fevereiro": "02",
            "março": "03",
            "abril": "04",
            "maio": "05",
            "junho": "06",
            "julho": "07",
            "agosto": "08",
            "setembro": "09",
            "outubro": "10",
            "novembro": "11",
            "dezembro": "12",
        }

        # Tentar extrair mês e ano
        for month_pt, month_num in month_mapping.items():
            if month_pt in normalized:
                # Extrair ano (últimos 4 dígitos)
                year_match = re.search(r"(\d{4})", normalized)
                year = year_match.group(1) if year_match else ""

                if year:
                    return f"{month_num}/{year}"

        # Se for formato numérico (dd/mm/yyyy)
        date_match = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", normalized)
        if date_match:
            day, month, year = date_match.groups()
            return f"{month.zfill(2)}/{year}"

        return normalized

    def _select_specific_installment(self, target_date: str) -> bool:
        """
        Seleciona uma parcela específica baseada na data
        """
        try:
            print(f"🔍 Procurando parcela com vencimento: {target_date}")

            # Normalizar a data alvo
            normalized_target = self._normalize_date(target_date)
            print(f"📅 Data normalizada para busca: {normalized_target}")

            # Procurar todas as parcelas
            installment_selectors = [
                ".installment-item-content",
                ".installment-item",
                "[class*='installment']",
                "//div[contains(@class, 'installment')]",
                "//div[contains(@class, 'parcela')]",
            ]

            installment_items = []
            for selector in installment_selectors:
                try:
                    if selector.startswith("//"):
                        items = self.driver.find_elements(By.XPATH, selector)
                    else:
                        items = self.driver.find_elements(By.CSS_SELECTOR, selector)

                    if items:
                        installment_items = items
                        break
                except:
                    continue

            if not installment_items:
                print("❌ Nenhuma parcela encontrada")
                return False

            print(f"📊 Encontradas {len(installment_items)} parcelas")

            for item in installment_items:
                try:
                    # Extrair informações da parcela
                    item_text = item.text.lower()
                    print(f"📄 Texto da parcela: {item_text[:100]}...")

                    # Procurar por data de vencimento
                    due_date = None
                    reference = None

                    # Tentar diferentes padrões para encontrar a data
                    date_patterns = [
                        r"vencimento.*?(\d{1,2}/\d{1,2}/\d{4})",
                        r"vencimento.*?(\d{1,2} de [a-z]+ de \d{4})",
                        r"vencimento.*?([a-z]+/\d{4})",
                        r"(\d{1,2}/\d{1,2}/\d{4})",
                        r"(\d{1,2} de [a-z]+ de \d{4})",
                        r"([a-z]+/\d{4})",
                    ]

                    for pattern in date_patterns:
                        match = re.search(pattern, item_text, re.IGNORECASE)
                        if match:
                            due_date = match.group(1).lower()
                            break

                    # Procurar referência (mês/ano)
                    ref_patterns = [
                        r"referência.*?([a-z]+/\d{4})",
                        r"referência.*?(\d{1,2}/\d{4})",
                        r"([a-z]+/\d{4})",
                        r"(\d{1,2}/\d{4})",
                    ]

                    for pattern in ref_patterns:
                        match = re.search(pattern, item_text, re.IGNORECASE)
                        if match:
                            reference = match.group(1).lower()
                            break

                    print(f"📅 Data encontrada: {due_date}, Referência: {reference}")

                    # Verificar se é a parcela desejada
                    found = False
                    if due_date:
                        normalized_due = self._normalize_date(due_date)
                        if normalized_target in normalized_due:
                            found = True
                            print(f"✅ Encontrada pela data: {due_date}")

                    if not found and reference:
                        normalized_ref = self._normalize_date(reference)
                        if normalized_target in normalized_ref:
                            found = True
                            print(f"✅ Encontrada pela referência: {reference}")

                    # Verificar também no texto completo
                    if not found and normalized_target in item_text:
                        found = True
                        print(f"✅ Encontrada no texto da parcela")

                    if found:
                        print(f"🎯 Parcela encontrada: {item_text[:50]}...")

                        # Procurar botão Pagar
                        pay_button_selectors = [
                            ".btn-pay",
                            "button:contains('Pagar')",
                            "//button[contains(text(), 'Pagar')]",
                            "//a[contains(text(), 'Pagar')]",
                        ]

                        pay_button = None
                        for btn_selector in pay_button_selectors:
                            try:
                                if ":contains" in btn_selector:
                                    pay_button = item.find_element(
                                        By.XPATH, ".//button[contains(text(), 'Pagar')]"
                                    )
                                elif btn_selector.startswith("//"):
                                    pay_button = item.find_element(
                                        By.XPATH, btn_selector
                                    )
                                else:
                                    pay_button = item.find_element(
                                        By.CSS_SELECTOR, btn_selector
                                    )

                                if pay_button and pay_button.is_displayed():
                                    break
                            except:
                                continue

                        if pay_button:
                            self.driver.execute_script(
                                "arguments[0].scrollIntoView({block: 'center'});",
                                pay_button,
                            )
                            time.sleep(1)
                            self.driver.execute_script(
                                "arguments[0].click();", pay_button
                            )
                            print("✅ Clicou no botão Pagar da parcela selecionada")
                            time.sleep(3)
                            return True
                        else:
                            print("❌ Botão Pagar não encontrado nesta parcela")

                except Exception as e:
                    print(f"   ⚠️ Erro ao processar parcela: {e}")
                    continue

            print("❌ Parcela não encontrada com a data especificada")
            return False

        except Exception as e:
            print(f"❌ Erro ao selecionar parcela: {str(e)}")
            return False

    def _click_first_pay_button(self) -> bool:
        """
        Clica no primeiro botão Pagar disponível
        """
        try:
            print("🔍 Procurando primeiro botão Pagar...")

            pay_button_selectors = [
                "//button[contains(text(), 'Pagar')]",
                "//button[contains(@class, 'btn-pay')]",
                "//a[contains(text(), 'Pagar')]",
                ".btn-pay",
                "button:contains('Pagar')",
            ]

            pay_button = None
            for selector in pay_button_selectors:
                try:
                    if ":contains" in selector:
                        pay_button = self.driver.find_element(
                            By.XPATH, "//button[contains(text(), 'Pagar')]"
                        )
                    elif selector.startswith("//"):
                        pay_button = self.driver.find_element(By.XPATH, selector)
                    else:
                        pay_button = self.driver.find_element(By.CSS_SELECTOR, selector)

                    if (
                        pay_button
                        and pay_button.is_displayed()
                        and pay_button.is_enabled()
                    ):
                        break
                    else:
                        pay_button = None
                except:
                    continue

            if not pay_button:
                print("❌ Nenhum botão Pagar encontrado")
                return False

            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", pay_button
            )
            time.sleep(1)
            self.driver.execute_script("arguments[0].click();", pay_button)
            print("✅ Clicou no primeiro botão Pagar")
            time.sleep(3)
            return True
        except Exception as e:
            print(f"❌ Não conseguiu clicar em Pagar: {str(e)}")
            return False

    def _click_go_to_payment_button(self) -> bool:
        """
        Clica no botão "Ir para pagamento"
        """
        try:
            print("🔍 Procurando botão 'Ir para pagamento'...")

            # Aguardar o botão aparecer
            time.sleep(3)

            go_to_payment_selectors = [
                "button.btn.btn-success.btn-to-pay",
                "button:contains('Ir para pagamento')",
                ".btn-to-pay",
                "//button[contains(text(), 'Ir para pagamento')]",
                "//button[.//i[contains(@class, 'fa-dollar')]]",
            ]

            go_to_payment_button = None
            for selector in go_to_payment_selectors:
                try:
                    if ":contains(" in selector:
                        go_to_payment_button = self.driver.find_element(
                            By.XPATH, "//button[contains(text(), 'Ir para pagamento')]"
                        )
                    elif selector.startswith("//"):
                        go_to_payment_button = self.driver.find_element(
                            By.XPATH, selector
                        )
                    else:
                        go_to_payment_button = self.driver.find_element(
                            By.CSS_SELECTOR, selector
                        )

                    if go_to_payment_button and go_to_payment_button.is_displayed():
                        break
                except:
                    continue

            if not go_to_payment_button:
                print("❌ Botão 'Ir para pagamento' não encontrado")
                return False

            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", go_to_payment_button
            )
            time.sleep(1)
            self.driver.execute_script("arguments[0].click();", go_to_payment_button)
            print("✅ Clicou no botão 'Ir para pagamento'")
            time.sleep(5)  # Aguardar mais tempo para carregar a página de pagamento
            return True

        except Exception as e:
            print(f"❌ Erro ao clicar em 'Ir para pagamento': {str(e)}")
            return False

    def handle_modal_and_generate_pix(self) -> Optional[Dict[str, Any]]:
        """
        Manipula o modal que abriu e gera o QR Code PIX
        """
        try:
            print("🎯 Procurando botão para gerar PIX...")

            # Aguardar carregamento da página de pagamento
            time.sleep(5)

            # Primeiro, verificar se já estamos em uma página com QR Code visível
            result = self.extract_pix_qr_code()
            if result and result.get("success"):
                print("✅ QR Code PIX já está visível na página")
                return result

            # Se não encontrou, procurar pelo botão de gerar PIX
            print("🔍 Procurando botão para gerar código PIX...")

            # Tentar encontrar o botão de forma mais abrangente
            pix_button_selectors = [
                "//button[contains(., 'PIX')]",
                "//button[contains(., 'pix')]",
                "//button[contains(., 'Pix')]",
                "//button[contains(., 'Gerar')]",
                "//button[contains(., 'gerar')]",
                "//button[contains(., 'Código')]",
                "//button[contains(., 'código')]",
                "//button[contains(., 'QR')]",
                "//button[contains(., 'qr')]",
                "//*[@id='btnPix']",
                "//*[contains(@onclick, 'PIX')]",
                "//*[contains(@onclick, 'pix')]",
                "//*[contains(@data-method, 'PIX')]",
                "//*[contains(@class, 'pix')]",
                "//*[contains(@class, 'PIX')]",
                "//a[contains(., 'PIX')]",
                "//a[contains(., 'pix')]",
            ]

            pix_button = None
            for selector in pix_button_selectors:
                try:
                    pix_button = self.driver.find_element(By.XPATH, selector)
                    if (
                        pix_button
                        and pix_button.is_displayed()
                        and pix_button.is_enabled()
                    ):
                        print(f"✅ Botão PIX encontrado com seletor: {selector}")
                        break
                    else:
                        pix_button = None
                except:
                    continue

            if not pix_button:
                print("❌ Botão PIX não encontrado. Verificando página atual...")
                print(f"📄 URL atual: {self.driver.current_url}")
                print(f"📄 Título da página: {self.driver.title}")

                # Salvar screenshot para debug
                try:
                    self.driver.save_screenshot("debug_pix_page.png")
                    print("📸 Screenshot salva como 'debug_pix_page.png'")
                except:
                    pass

                # Tentar extrair QR Code novamente (pode já estar visível)
                result = self.extract_pix_qr_code()
                if result and result.get("success"):
                    return result

                return None

            # Clicar no botão PIX
            print("🖱️ Clicando no botão PIX...")
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});",
                pix_button,
            )
            time.sleep(1)

            # Tentar clique normal primeiro
            try:
                pix_button.click()
                print("✅ Clique normal no botão PIX")
            except:
                # Se falhar, tentar clique via JavaScript
                try:
                    self.driver.execute_script("arguments[0].click();", pix_button)
                    print("✅ Clique via JavaScript no botão PIX")
                except Exception as e:
                    print(f"❌ Erro ao clicar no botão PIX: {e}")
                    return None

            # Aguardar geração do QR Code
            print("⏳ Aguardando geração do QR Code PIX...")
            time.sleep(8)  # Dar mais tempo para gerar

            # Extrair código PIX
            return self.extract_pix_qr_code()

        except Exception as e:
            print(f"❌ Erro ao manipular modal PIX: {str(e)}")
            return None

    def extract_pix_qr_code(self) -> Optional[Dict[str, Any]]:

        try:
            print("🔍 Procurando QR Code PIX...")
            time.sleep(3)

            # Primeiro, procurar código PIX em texto (copia e cola)
            pix_code = None

            # Seletores específicos baseados no HTML fornecido
            text_selectors = [
                "//input[@class='copy-input']",
                "//input[@id='copy-input']",
                "//input[contains(@class, 'copy-input')]",
                "//input[contains(@onclick, 'copyFunction')]",
                "//input[@readonly and contains(@value, '00020101')]",
                # Seletores mais genéricos
                "//input[contains(@value, '00020101')]",
                "//input[contains(@value, 'br.gov.bcb.pix')]",
                "//textarea[contains(text(), '00020101')]",
            ]

            for selector in text_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element.is_displayed():
                        # Tentar diferentes métodos para obter o valor
                        text = (
                            element.get_attribute("value")
                            or element.text.strip()
                            or element.get_attribute("textContent")
                            or element.get_attribute("innerHTML")
                        )

                        if text and ("000201" in text or "br.gov.bcb.pix" in text):
                            # Limpar o texto e validar se é um código PIX válido
                            clean_text = (
                                text.strip().replace("\n", "").replace("\r", "")
                            )

                            # Validar se começa com 00020101 (padrão PIX)
                            if clean_text.startswith("00020101"):
                                pix_code = clean_text
                                print(
                                    f"✅ Código PIX encontrado via seletor: {selector}"
                                )
                                print(
                                    f"💰 Tamanho do código: {len(pix_code)} caracteres"
                                )
                                break

                except:
                    # Silenciosamente continuar para o próximo seletor
                    continue

            # Se não encontrou pelos seletores específicos, procurar na página toda
            if not pix_code:
                print("🔍 Procurando PIX no código fonte da página...")
                page_source = self.driver.page_source

                # Padrões para encontrar códigos PIX
                pix_patterns = [
                    r'value="(00020101[^"]{100,})"',  # Dentro de value=""
                    r"value='(00020101[^']{100,})'",  # Dentro de value=''
                    r">(00020101[0-9A-Za-z+=/\-\.]{100,})<",  # Entre tags
                    r"(00020101021[0-9A-Za-z+=/\-\.]{100,})",  # Padrão geral PIX
                ]

                for pattern in pix_patterns:
                    match = re.search(pattern, page_source)
                    if match:
                        potential_code = match.group(1)
                        # Validar se é um código PIX válido (deve ter pelo menos 100 caracteres)
                        if len(potential_code) >= 100:
                            pix_code = potential_code
                            print("✅ Código PIX encontrado no código fonte da página")
                            break

            # Procurar por QR Code em imagem
            qr_image_url = None
            qr_selectors = [
                # Seletores específicos baseados no HTML
                "//div[@class='qr_code']//img",
                "//img[@alt='QRCode']",
                "//img[contains(@src, 'data:image/png;base64')]",
                # Seletores mais genéricos
                "//img[contains(@src, 'qr')]",
                "//img[contains(@alt, 'QR')]",
                "//img[contains(@alt, 'PIX')]",
                "//img[contains(@src, 'pix')]",
                "//img[contains(@class, 'qr')]",
                "//img[contains(@class, 'pix')]",
                "//canvas[contains(@class, 'qr')]",
                "//canvas[contains(@class, 'pix')]",
                "//*[@id='qrcode']//img",
                "//*[contains(@class, 'qrcode')]//img",
            ]

            for selector in qr_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    if element.is_displayed():
                        qr_image_url = element.get_attribute("src")
                        if qr_image_url and (
                            "http" in qr_image_url or "data:image" in qr_image_url
                        ):
                            print(f"✅ Imagem QR encontrada via seletor: {selector}")
                            break
                except:
                    continue

            # Tentar extrair dados adicionais do PIX (valor, destinatário, etc.)
            additional_data = {}

            try:
                # Procurar valor do PIX
                valor_selectors = [
                    "//span[contains(text(), 'R$')]",
                    "//*[contains(text(), 'Valor')]/following-sibling::*",
                    "//*[contains(text(), 'R$ ')]",
                ]

                for selector in valor_selectors:
                    try:
                        element = self.driver.find_element(By.XPATH, selector)
                        text = element.text.strip()
                        if "R$" in text:
                            additional_data["valor"] = text
                            break
                    except:
                        continue

                # Procurar nome do aluno/destinatário
                nome_selectors = [
                    "//*[contains(text(), 'Aluno')]/following-sibling::*",
                    "//span[contains(text(), 'Douglas')]",
                    "//*[contains(@class, 'aluno')]",
                ]

                for selector in nome_selectors:
                    try:
                        element = self.driver.find_element(By.XPATH, selector)
                        text = element.text.strip()
                        if (
                            text and len(text) > 5
                        ):  # Nome deve ter mais que 5 caracteres
                            additional_data["destinatario"] = text
                            break
                    except:
                        continue

                # Procurar data de validade
                validade_selectors = [
                    "//*[contains(text(), 'válido até')]",
                    "//*[contains(text(), 'valido até')]",
                    "//h3[contains(text(), 'até')]",
                ]

                for selector in validade_selectors:
                    try:
                        element = self.driver.find_element(By.XPATH, selector)
                        text = element.text.strip()
                        if "até" in text.lower():
                            additional_data["validade"] = text
                            break
                    except:
                        continue

            except Exception as e:
                print(f"⚠️ Erro ao extrair dados adicionais: {str(e)}")

            result = {
                "pix_code": pix_code,
                "qr_image_url": qr_image_url,
                "additional_data": additional_data,
                "success": bool(pix_code or qr_image_url),
                "timestamp": datetime.now().isoformat(),
            }

            if result["success"]:
                print("✅ QR Code PIX encontrado!")
                if pix_code:
                    print(f"💰 Código PIX (início): {pix_code[:50]}...")
                    print(f"📏 Tamanho total: {len(pix_code)} caracteres")
                if qr_image_url:
                    print(f"🖼️ URL da imagem QR: {qr_image_url[:100]}...")
                if additional_data:
                    print(f"📋 Dados adicionais: {additional_data}")
            else:
                print("❌ QR Code PIX não encontrado")
                # Debug: mostrar parte do source para ajudar
                try:
                    # Procurar por qualquer input com value longo
                    inputs = self.driver.find_elements(By.XPATH, "//input[@value]")
                    for inp in inputs[:5]:  # Apenas os primeiros 5
                        value = inp.get_attribute("value")
                        if value and len(value) > 50:
                            print(
                                f"🔍 Input encontrado com value longo: {value[:100]}..."
                            )

                    # Mostrar preview do source
                    source_preview = self.driver.page_source[:2000]
                    if "00020101" in source_preview:
                        print("🔍 Código PIX detectado no preview do source!")
                    else:
                        print("🔍 Nenhum código PIX no preview do source")
                except Exception as debug_e:
                    print(f"⚠️ Erro no debug: {str(debug_e)}")

            return result

        except Exception as e:
            print(f"❌ Erro ao extrair QR Code: {str(e)}")
            import traceback

            print(f"🔍 Traceback completo: {traceback.format_exc()}")
            return None

    def get_pix_qr_code(
        self, cpf: str, birth_date: str, target_date: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Método principal para obter o QR Code PIX
        """
        try:
            print("🚀 Iniciando processo de obtenção do QR Code PIX...")

            # 1. Fazer login
            if not self.login(cpf, birth_date):
                return None

            # 2. Navegar para pagamento (com seleção opcional de parcela)
            if not self.navigate_to_payment(target_date):
                return None

            # 3. Manipular modal e gerar PIX
            result = self.handle_modal_and_generate_pix()

            return result

        except Exception as e:
            print(f"❌ Erro no processo principal: {str(e)}")
            return None


def main():
    """Exemplo de uso do scraper"""
    # Configurações
    CPF = "015.966.702-07"
    BIRTH_DATE = "09-16-1993"

    # Solicitar data da parcela (opcional)
    target_date = input(
        "Digite a data da parcela desejada (ex: 10/09/2025, setembro/2025, dezembro/2025, ou deixe em branco para primeira parcela):"
    ).strip()

    if not target_date:
        print("Nenhuma data especificada, usando primeira parcela disponível")

    # Usar o scraper
    with PixScraperEducAdventista(headless=True) as scraper:
        result = scraper.get_pix_qr_code(CPF, BIRTH_DATE, target_date)

        if result and result.get("success"):
            print("Sucesso!")
            print(json.dumps(result, indent=2, ensure_ascii=False))

            # Salvar resultado em arquivo
            filename = f"pix_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"Resultado salvo em '{filename}'")

        else:
            print("Falha ao obter QR Code PIX")


if __name__ == "__main__":
    main()
