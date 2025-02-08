import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import os

# Função para instalar as dependências do sistema
def instalar_dependencias():
    try:
        # Instalar o Chromium no Streamlit Cloud
        os.system("apt-get update")
        os.system("apt-get install -y chromium-browser")
        os.system("apt-get install -y libnss3 libgconf-2-4 libgdk-pixbuf2.0-0 fonts-liberation")
    except Exception as e:
        st.error(f"Erro ao instalar dependências: {e}")

# Função para iniciar o WebDriver
def iniciar_driver(exibir_navegador=False):
    # Instalar dependências necessárias
    instalar_dependencias()

    # Configurar opções do Chromium
    options = Options()
    options.add_argument("--headless")  # Modo headless para rodar em ambiente sem interface gráfica
    options.add_argument("--disable-gpu")  # Para evitar falhas em ambientes sem GPU
    options.add_argument("--no-sandbox")  # Necessário para ambientes Docker ou de nuvem
    options.add_argument("--disable-dev-shm-usage")  # Impede erros de memória no container
    options.binary_location = "/usr/bin/chromium-browser"  # Caminho do Chromium no Streamlit Cloud

    # Instalar o driver compatível
    driver_path = ChromeDriverManager().install()

    # Instalar o serviço do WebDriver
    service = Service(driver_path)
    
    try:
        # Iniciar o WebDriver com as opções configuradas
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        st.error(f"Erro ao inicializar o WebDriver: {e}")
        return None

# Função para rolar e carregar resultados
def rolar_e_carregar_resultados(driver, tempo_espera=10, max_tentativas=50):
    prev_height = driver.execute_script("return document.body.scrollHeight")
    for tentativa in range(max_tentativas):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(tempo_espera)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == prev_height:
            break
        prev_height = new_height

# Interface no Streamlit
st.title("Busca de Empresas no Google Maps")

# Inputs
localizacao = st.text_input("Localização:", "São Paulo, SP")
palavra_chave = st.text_input("Palavra-chave:", "Restaurantes")

# Botão para iniciar a busca
if st.button("Iniciar Busca"):
    if not localizacao or not palavra_chave:
        st.warning("Por favor, preencha a localização e a palavra-chave.")
    else:
        driver = iniciar_driver(exibir_navegador=True)

        if driver:
            st.write("Buscando empresas no Google Maps...")
            url = f"https://www.google.com/maps/search/{palavra_chave}+em+{localizacao}/"
            driver.get(url)
            rolar_e_carregar_resultados(driver)

            # Exemplo de como pegar o primeiro resultado
            try:
                resultado = driver.find_element_by_class_name("Nv2PK")
                nome_empresa = resultado.text
                st.write(f"Resultado: {nome_empresa}")
            except Exception as e:
                st.error(f"Erro ao buscar resultados: {e}")
            
            # Fechar o driver após a busca
            driver.quit()
