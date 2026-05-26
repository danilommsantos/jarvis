import queue
import threading

_lock = threading.Lock()
_estado = {
    'rodando': False,
    'fila': queue.Queue(),
    'gerencial_pronto': threading.Event(),
}


def iniciar():
    with _lock:
        _estado['rodando'] = True
        _estado['gerencial_pronto'].clear()
        # Limpa eventos anteriores
        while not _estado['fila'].empty():
            try:
                _estado['fila'].get_nowait()
            except queue.Empty:
                break


def push(evento):
    _estado['fila'].put(evento)


def esta_rodando():
    return _estado['rodando']


def finalizar():
    with _lock:
        _estado['rodando'] = False
    _estado['fila'].put(None)  # sentinel para encerrar o stream


def get_fila():
    return _estado['fila']


def aguardar_gerencial():
    _estado['gerencial_pronto'].wait()


def sinalizar_gerencial_pronto():
    _estado['gerencial_pronto'].set()
