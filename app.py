import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
from datetime import datetime
from geopy.geocoders import Nominatim
import os

# Função para iniciar o WebDriver com webdriver_manager
def iniciar_driver(exibir_navegador=False):
    options = Options()
    options.add_argument("--headless")  # Garante que o navegador rode em modo headless
    options.add_argument("--disable-gpu")  # Para evitar falhas em ambientes sem GPU
    options.add_argument("--no-sandbox")  # Necessário para ambientes Docker ou de nuvem
    options.add_argument("--disable-dev-shm-usage")  # Impede erros de memória no container

    # Usar o ChromeDriverManager para instalar o ChromeDriver
    service = Service(ChromeDriverManager().install())
    
    try:
        driver = webdriver.Chrome(service=service, options=options)
        return driver
    except Exception as e:
        st.error(f"Erro ao inicializar o WebDriver: {e}")
        return None

# Função para esperar um elemento
def esperar_elemento(driver, by_, value, timeout=10):
    try:
        return WebDriverWait(driver, timeout).until(EC.presence_of_element_located((by_, value)))
    except Exception as e:
        st.error(f"Erro ao esperar elemento: {e}")
        return None

# Função para rolar a página com zoom inteligente
def rolar_e_carregar_resultados(driver, tempo_espera=10, max_tentativas=50, zoom=False):
    prev_height = driver.execute_script("return document.body.scrollHeight")
    for tentativa in range(max_tentativas):
        if zoom:
            driver.execute_script("document.body.style.zoom='120%'")
            time.sleep(2)
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(tempo_espera)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == prev_height:
            break
        prev_height = new_height

# Função para geocodificação reversa usando geopy
def obter_dados_endereco(latitude, longitude):
    geolocator = Nominatim(user_agent="google_maps_scraper", timeout=10)
    try:
        location = geolocator.reverse((latitude, longitude), language='pt')
        if location:
            endereco = location.raw['address']
            cidade = endereco.get('city', 'N/A')
            bairro = endereco.get('suburb', 'N/A')
            estado = endereco.get('state', 'N/A')
            return cidade, bairro, estado
        else:
            return 'N/A', 'N/A', 'N/A'
    except Exception as e:
        st.error(f"Erro na geocodificação: {e}")
        return 'N/A', 'N/A', 'N/A'

# Função para buscar empresas no Google Maps
def buscar_no_google_maps(driver, localizacao, palavra_chave, zoom=True):
    url = f"https://www.google.com/maps/search/{palavra_chave}+em+{localizacao}/"
    driver.get(url)

    if not esperar_elemento(driver, By.CLASS_NAME, "Nv2PK"):
        st.warning(f"Resultados não carregaram para {palavra_chave} em {localizacao}")
        return []

    rolar_e_carregar_resultados(driver, zoom=zoom)

    resultados = driver.find_elements(By.CLASS_NAME, "Nv2PK")
    empresas = []
    empresas_seen = set()  # Para evitar duplicados

    for resultado in resultados:
        try:
            nome = resultado.find_element(By.CLASS_NAME, "qBF1Pd").text
            if not nome.strip() or nome in empresas_seen:  # Ignorar empresas sem nome e duplicadas
                continue
            empresas_seen.add(nome)
            
            Rating_avaliadores_nivel_preco = resultado.find_element(By.CLASS_NAME, "W4Efsd").text
            avaliacao = resultado.find_element(By.CLASS_NAME, "MW4etd").text
            telefone = resultado.find_element(By.CLASS_NAME, "xQ82C").text if resultado.find_elements(By.CLASS_NAME, "xQ82C") else "N/A"
            site = resultado.find_element(By.CLASS_NAME, "F7nice").text if resultado.find_elements(By.CLASS_NAME, "F7nice") else "N/A"
            total_avaliadores = resultado.find_element(By.CLASS_NAME, "UY7F9").text

            # Extração da nota (rating), número de avaliadores e faixa de preço
            rating = Rating_avaliadores_nivel_preco.split("(")[0].strip().replace(",", ".") if "(" in Rating_avaliadores_nivel_preco else "N/A"
            avaliadores = Rating_avaliadores_nivel_preco.split("(")[1].split(")")[0] if "(" in Rating_avaliadores_nivel_preco else "N/A"
            nivel_preco = Rating_avaliadores_nivel_preco.split("·")[1].strip() if "·" in Rating_avaliadores_nivel_preco else "N/A"

            # Captura de novos elementos
            servicosExtras = resultado.find_element(By.CLASS_NAME, "hfpxzc").text if resultado.find_elements(By.CLASS_NAME, "hfpxzc") else "N/A"
            Informações_completa = resultado.find_element(By.CLASS_NAME, "lI9IFe").text if resultado.find_elements(By.CLASS_NAME, "lI9IFe") else "N/A"

            # Link
            link = resultado.find_element(By.CLASS_NAME, "hfpxzc").get_attribute("href") if resultado.find_elements(By.CLASS_NAME, "hfpxzc") else "N/A"

            # Extraindo latitude, longitude e Place ID do link
            latitude = link.split("!8m2!3d")[1].split("!4d")[0] if "!8m2!3d" in link else "N/A"
            longitude = link.split("!4d")[1].split("!16s")[0] if "!4d" in link else "N/A"
            placeId = f"ChI{link.split('?')[0].split('ChI')[1]}" if "ChI" in link else "N/A"

            # Obtendo dados de endereço
            cidade, bairro, estado = obter_dados_endereco(latitude, longitude)

            # Adicionando a data atual
            data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Adicionando fotos, se disponíveis
            fotos = resultado.find_elements(By.CLASS_NAME, "FQ2IWe p0Hhde")  # Usando a classe correta
            fotos_urls = [foto.find_element(By.TAG_NAME, "img").get_attribute("src") for foto in fotos]

            empresas.append({
                'nome': nome,
                'Rating_avaliadores_nivel_preco': Rating_avaliadores_nivel_preco, 
                'avaliacao': avaliacao,
                'total_avaliadores': avaliadores,
                'telefone': telefone, 
                'site': site,
                'servicosExtras': servicosExtras,
                'Informações_completa': Informações_completa,
                'URL': link,
                'Data_Recentes': data_atual,
                'latitude': latitude,
                'longitude': longitude,
                'placeId': placeId,
                'rating': rating,
                'avaliadores': avaliadores,
                'nivel_preco': nivel_preco,
                'cidade': cidade,
                'bairro': bairro,
                'estado': estado,
                'fotos': fotos_urls
            })
        except Exception as e:
            st.error(f"Erro ao processar empresa: {e}")

    return empresas

# Interface no Streamlit
st.title("Busca de Empresas no Google Maps")

# Exibir modelo do arquivo XLSX
modelo = pd.DataFrame({
    'Localizacao': ['São Paulo, SP', 'Rio de Janeiro, RJ', 'Belo Horizonte, MG'],
    'Palavra_Chave': ['Restaurantes, Pizzarias', 'Supermercados, Lojas', 'Restaurantes, Cafés']
})

# Caminho absoluto para salvar o arquivo
modelo_arquivo = os.path.join(os.getcwd(), "queries/modelo.xlsx")
modelo.to_excel(modelo_arquivo, index=False)

# Interface do Streamlit

# Upload de arquivo ou entrada manual
arquivo = st.sidebar.file_uploader("Carregar arquivo XLSX", type="xlsx")

#st.sidebar.header("Modelo do Arquivo XLSX")
#st.sidebar.write("O arquivo XLSX deve ter as seguintes colunas: 'Localizacao' e 'Palavra_Chave'.")
st.sidebar.write("Exemplo de formato do arquivo:")
#st.sidebar.table(modelo)

# Botão para download do arquivo
with open(modelo_arquivo, "rb") as f:
    st.sidebar.download_button(
        label="Baixar Arquivo Modelo XLSX",
        data=f,
        file_name="modelo.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

localizacoes, palavras_chave = [], []
if arquivo:
    df = pd.read_excel(arquivo)
    localizacoes = df['Localizacao'].dropna().tolist()
    palavras_chave = df['Palavra_Chave'].dropna().tolist()
else:
    localizacoes = st.text_input("Localizações (separadas por vírgula):", "São Paulo, SP").split(",")
    palavras_chave = st.text_input("Palavras-chave (separadas por vírgula):", "Restaurantes, Cafés").split(",")

# Opções de configuração
exibir_navegador = st.sidebar.checkbox("Exibir Navegador", value=True)

if st.button("Iniciar Busca"):
    if not localizacoes or not palavras_chave:
        st.warning("Por favor, preencha as localizações e palavras-chave.")
    else:
        driver = iniciar_driver(exibir_navegador)
        empresas = []

        if driver:
            with st.spinner("Buscando empresas..."):
                for local in localizacoes:
                    for palavra in palavras_chave:
                        resultados = buscar_no_google_maps(driver, local.strip(), palavra.strip())
                        empresas.extend(resultados)

            driver.quit()

            if empresas:
                st.success(f"Busca concluída! {len(empresas)} resultados encontrados.")
                df_resultados = pd.DataFrame(empresas)
                st.dataframe(df_resultados)

                @st.cache_data
                def gerar_xlsx(dataframe):
                    arquivo_saida = f"resultado/resultados_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
                    dataframe.to_excel(arquivo_saida, index=False)
                    return arquivo_saida

                arquivo_saida = gerar_xlsx(df_resultados)
                with open(arquivo_saida, 'rb') as f:
                    st.download_button("Baixar Resultados", data=f, file_name=arquivo_saida, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                st.warning("Nenhum resultado encontrado.")
        else:
            st.error("Erro ao inicializar o driver. Verifique as configurações.")
