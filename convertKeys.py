#convertir las credenciales JSON a un formato para guardarlo como secrets.


import json

with open("keys.json", "r") as file:
    key_dict = json.load(file)

key_string = json.dumps(key_dict)

with open(".streamlit/secrets.toml", "w") as file:
    file.write('textkey = """')
    file.write(key_string)
    file.write('"""')

print("Archivo secrets.toml creado correctamente")