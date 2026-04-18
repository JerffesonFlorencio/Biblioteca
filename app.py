from datetime import datetime, time
from time import sleep
from api.src.functions.logs.index import log
from api.src.main import inicia_processo_da_automação #exemplo

HORAIO_AGENDADO = "22:22" 
    
def main():
    log.info("Iniciando o processo de automação...")
    while True:
        now = datetime.now().strftime("%H:%M")
        if now == HORAIO_AGENDADO:
            inicia_processo_da_automação()
            log.info(f"Processo de automação finalizado. Hora atual: {now}...")
            sleep(60)
        
        else:
            log.info(f"Hora atual: {now}. Aguardando o horário agendado: {HORAIO_AGENDADO}...", end="\r")
            sleep(60)
        
if __name__ == "__main__":
    log.info("Iniciando o processo ...")
    main()
