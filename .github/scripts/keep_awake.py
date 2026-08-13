"""
Visita o painel publicado no Streamlit Community Cloud, simulando um navegador de verdade
(não uma requisição HTTP simples) — necessário porque o Streamlit parece exigir uma conexão
completa (que abre um WebSocket) para resetar o contador de inatividade de 12 horas.

Se o app estiver "dormindo" no momento da visita, esse script também clica automaticamente
no botão "Yes, get this app back up!" para acordá-lo.

Uso (local, para testar):
    pip install playwright
    playwright install chromium
    python .github/scripts/keep_awake.py

No GitHub Actions, isso roda automaticamente — ver .github/workflows/keep_streamlit_awake.yml
"""

import sys
import time
from playwright.sync_api import sync_playwright

URL_DO_PAINEL = "https://dcnt-santa-catarina.streamlit.app/"


def visitar_e_acordar(url: str) -> bool:
    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=True)
        pagina = navegador.new_page()

        print(f"[INFO] Acessando: {url}")
        pagina.goto(url, timeout=60_000, wait_until="domcontentloaded")

        # Dá um tempo para o Streamlit terminar de carregar / detectar se está "dormindo"
        time.sleep(5)

        # Se o app estiver dormindo, aparece um botão com esse texto — procura e clica nele
        try:
            botao_acordar = pagina.get_by_text("get this app back up", exact=False)
            if botao_acordar.is_visible(timeout=5_000):
                print("[INFO] App estava dormindo — clicando para acordar...")
                botao_acordar.click()
                time.sleep(15)  # espera o app subir de verdade
                print("[OK] Comando de acordar enviado.")
            else:
                print("[OK] App já estava acordado — visita registrada normalmente.")
        except Exception:
            print("[OK] Nenhum botão de 'acordar' encontrado — app já estava ativo.")

        navegador.close()
        return True


if __name__ == "__main__":
    try:
        visitar_e_acordar(URL_DO_PAINEL)
        print("[SUCESSO] Visita concluída.")
    except Exception as e:
        print(f"[ERRO] Falha ao visitar o painel: {e}")
        sys.exit(1)
