import socket


def get_paths():
    if any([x in socket.gethostname() for x in ['datascience', 'frontend']]):
        import htcal_path_eve as htpath
    elif any([x in socket.gethostname() for x in ['juwels']]):
        import htcal_path_juwels as htpath
    else:
        raise Error('cannot import paths, check if running')
    return htpath
