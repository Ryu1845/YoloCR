import PySimpleGUIQt as sg

# Design pattern 2 - First window remains active

layout = [
    [
        sg.Text("Window 1"),
    ],
    [sg.Input(do_not_clear=True)],
    [sg.Text(size=(15, 1), key="-OUTPUT-")],
    [sg.Button("Launch 2"), sg.Button("Exit")],
]

win1 = sg.Window("Window 1", layout)

win2_active = False
while True:
    ev1, vals1 = win1.read(timeout=100)
    win1["-OUTPUT-"].update(vals1[0])
    if ev1 in (sg.WIN_CLOSED, "Exit"):
        break

    if not win2_active and ev1 == "Launch 2":
        win2_active = True
        layout2 = [[sg.Text("Window 2")], [sg.InputText()], [sg.Button("Exit")]]

        win2 = sg.Window("Window 2", layout2)

    if win2_active:
        ev2, vals2 = win2.read(timeout=100)
        if ev2 in (sg.WIN_CLOSED, "Exit"):
            win2_active = False
            win2.close()
