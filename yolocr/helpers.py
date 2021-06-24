import os


class In_dir:
    def __init__(self, path):
        self.path = path
        self.old_path = os.getcwd()

    def __enter__(self):
        os.chdir(self.path)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        os.chdir(self.old_path)


def convert_secs(rough_time: float) -> str:
    """
    Convert seconds to human readable time
    Parameters
    ----------
    rough_time:
        time you want to convert in seconds
    Returns
    -------
    human readable time
    """
    h = rough_time // 3600
    m = (rough_time % 3600) // 60
    s = (rough_time % 60) // 1
    ms = (rough_time % 1) * 1000
    time_cvtd = f"{h:02.0f}h{m:02.0f}m{s:02.0f}s{ms:03.0f}"
    return time_cvtd
