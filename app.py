import streamlit as st
from playwright.sync_api import sync_playwright
import pandas as pd
import time
from datetime import datetime
from geopy.geocoders import Nominatim
import os

# Função para iniciar o Playwright
def iniciar_driver():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)  # Lançando o navegador em modo headless
        page = browser.new_page()
        return page, browser

# Função para esperar um elemento
def esperar_elemento(page, selector, timeout=10000):
    try:
        page.wait_for_selector(selector, timeout=timeout)
    except Exception as e:
        st.error(f"Erro ao esperar elemento: {e}")
        return None

# Função para rolar a página com zoom inteligente
def rolar_e_carregar_resultados(page, tempo_espera=10, max_tentativas=50, zoom=False):
    prev_height = page.evaluate("document.body.scrollHeight")
    for tentativa in range(max_tentativas):
        if zoom:
            page.evaluate("document.body.style.zoom='120%'")
            time.sleep(2)
        
        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(tempo_espera)
        new_height = page.evaluate("document.body.scrollHeight")
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
def buscar_no_google_maps(page, localizacao, palavra_chave, zoom=True):
    url = f"https://www.google.com/maps/search/{palavra_chave}+em+{localizacao}/"
    page.goto(url)

    if not esperar_elemento(page, "div.Nv2PK"):
        st.warning(f"Resultados não carregaram para {palavra_chave} em {localizacao}")
        return []

    rolar_e_carregar_resultados(page, zoom=zoom)

    resultados = page.query_selector_all("div.Nv2PK")
    empresas = []
    empresas_seen = set()  # Para evitar duplicados

    for resultado in resultados:
        try:
            nome = resultado.query_selector("div.qBF1Pd").inner_text()
            if not nome.strip() or nome in empresas_seen:  # Ignorar empresas sem nome e duplicadas
                continue
            empresas_seen.add(nome)
            
            Rating_avaliadores_nivel_preco = resultado.query_selector("div.W4Efsd").inner_text()
            avaliacao = resultado.query_selector("div.MW4etd").inner_text()
            telefone = resultado.query_selector("div.xQ82C").inner_text() if resultado.query_selector("div.xQ82C") else "N/A"
            site = resultado.query_selector("div.F7nice").inner_text() if resultado.query_selector("div.F7nice") else "N/A"
            total_avaliadores = resultado.query_selector("div.UY7F9").inner_text()

            # Extração da nota (rating), número de avaliadores e faixa de preço
            rating = Rating_avaliadores_nivel_preco.split("(")[0].strip().replace(",", ".") if "(" in Rating_avaliadores_nivel_preco else "N/A"
            avaliadores = Rating_avaliadores_nivel_preco.split("(")[1].split(")")[0] if "(" in Rating_avaliadores_nivel_preco else "N/A"
            nivel_preco = Rating_avaliadores_nivel_preco.split("·")[1].strip() if "·" in Rating_avaliadores_nivel_preco else "N/A"

            # Captura de novos elementos
            servicosExtras = resultado.query_selector("div.hfpxzc").inner_text() if resultado.query_selector("div.hfpxzc") else "N/A"
            Informações_completa = resultado.query_selector("div.lI9IFe").inner_text() if resultado.query_selector("div.lI9IFe") else "N/A"

            # Link
            link = resultado.query_selector("div.hfpxzc").get_attribute("href") if resultado.query_selector("div.hfpxzc") else "N/A"

            # Extraindo latitude, longitude e Place ID do link
            latitude = link.split("!8m2!3d")[1].split("!4d")[0] if "!8m2!3d" in link else "N/A"
            longitude = link.split("!4d")[1].split("!16s")[0] if "!4d" in link else "N/A"
            placeId = f"ChI{link.split('?')[0].split('ChI')[1]}" if "ChI" in link else "N/A"

            # Obtendo dados de endereço
            cidade, bairro, estado = obter_dados_endereco(latitude, longitude)

            # Adicionando a data atual
            data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Adicionando fotos, se disponíveis
            fotos = resultado.query_selector_all("div.FQ2IWe p0Hhde")  # Usando a classe correta
            fotos_urls = [foto.query_selector("img").get_attribute("src") for foto in fotos]

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

st.sidebar.write("Exemplo de formato do arquivo:")

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
        page, browser = iniciar_driver()
        empresas = []

        with st.spinner("Buscando empresas..."):
            for local in localizacoes:
                for palavra in palavras_chave:
                    resultados = buscar_no_google_maps(page, local.strip(), palavra.strip())
                    empresas.extend(resultados)

        browser.close()

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
