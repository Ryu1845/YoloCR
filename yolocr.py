def convert_secs(secs):
    secs = secs.split(".")[0]
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    ms = secs.split(".")[1]
    print(f"{h:02}{m:02}{s:02}{ms:03}")
