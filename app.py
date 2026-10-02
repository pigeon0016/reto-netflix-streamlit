import json
import pandas as pd
import streamlit as st

from google.cloud import firestore
from google.oauth2 import service_account
from sqlalchemy import create_engine, text

key_dict = json.loads(st.secrets["textkey"])
credentials = service_account.Credentials.from_service_account_info(key_dict)
#Esto convierte el diccionario en credenciales que Google entiende.



#conexion a firestore
db = firestore.Client(
    credentials=credentials,
    project=key_dict["project_id"]
)

#movies asi se llama la base q creamos en firestore
movies_ref = db.collection("movies")



# Conexión a PostgreSQL
postgres = st.secrets["postgres"]

postgres_url = (
    f"postgresql+psycopg2://{postgres['user']}:{postgres['password']}"
    f"@{postgres['host']}:{postgres['port']}/{postgres['database']}"
)

engine = create_engine( #engine será nuestra conexión con PostgreSQL.
    postgres_url,
    connect_args={"sslmode": "require"}
)



#leemos la coleccion de la base 
def load_movies():
    docs = movies_ref.stream() #le decimos a firebase dame los documentos de movies
    movies = [] #lista vacia

    for doc in docs:
        movie = doc.to_dict()
        movie["id"] = doc.id
        movies.append(movie)

    return pd.DataFrame(movies)

# Cargar películas al iniciar la aplicación (funciones de arranque)
df_movies = load_movies()
def filter_movies_by_director(dataframe, director):
    return dataframe[dataframe["director"] == director]
def add_movie(name, genre, director, company):
    doc_ref = movies_ref.document() #crea una referencia a un documento nuevo y Firestore genera automáticamente su ID.

    doc_ref.set({ #guarda los cuatro campos.
        "name": name,
        "genre": genre,
        "director": director,
        "company": company
    })
#función para registrar visitantes
def add_guest(email, comment):
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO people (email, comment)
                VALUES (:email, :comment)
                """
            ),
            {
                "email": email,
                "comment": comment
            }
        )
def load_guests():
    query = text(
        """
        SELECT email, comment
        FROM people
        """
    )

    with engine.connect() as connection:
        result = connection.execute(query)

        rows = result.fetchall()

    return pd.DataFrame(
        rows,
        columns=["email", "comment"]
    )
#-------------------------------------------


# Interfaz
st.title("Netflix app")
#st.caption("Demo - Loading data locally")

st.sidebar.header("Mostrar todos los filmes") #crea el encabezado en la barra lateral.


# la opcion de mostrar todos se activa
show_all = st.sidebar.checkbox("Todos los filmes") #muestra Todos los filmes

if show_all:
    st.header("Todos los filmes")
    st.dataframe(
        df_movies[["name", "genre", "director", "company"]],
        use_container_width=True
    )


# buscar por titulo
st.sidebar.markdown("---")
st.sidebar.subheader("Buscar filme")

movie_search = st.sidebar.text_input("Título del filme")
search_button = st.sidebar.button("Buscar filme")

if search_button:
    if movie_search:
        result = df_movies[
            df_movies["name"].str.contains( #.contrains hace posible que la busqueda no sea rigida
                movie_search,
                case=False, #Ignorar diferencias entre mayúsculas y minúsculas.
                na=False #Evita problemas si algún registro tuviera un valor vacío/nulo en name
            )
        ]

        st.header("Resultado de búsqueda")

        if result.empty:
            st.warning("No se encontraron filmes.")
        else:
            st.dataframe(
                result[["name", "genre", "director", "company"]],
                use_container_width=True
            )
    else:
        st.warning("Escribe un título para realizar la búsqueda.")

# directores

st.sidebar.markdown("---")
st.sidebar.subheader("Seleccionar director")

directors = sorted(
    df_movies["director"].dropna().unique().tolist() 
    #dropna elimina valores vacíos.
    #unique elimina duplicados.
    #to list lo convierte en una lista que selectbox puede utilizar.
    #sorted ordena los nombres.
)

selected_director = st.sidebar.selectbox(
    "Director",
    directors
)

# esto pone el boton
filter_button = st.sidebar.button("Filtrar director")


if filter_button:
    director_movies = filter_movies_by_director(
        df_movies,
        selected_director
    )

    st.header(f"Filmes de {selected_director}")

    st.write(f"Total filmes: {len(director_movies)}")

    st.dataframe(
        director_movies[["name", "genre", "director", "company"]],
        use_container_width=True
    )


#Formulario para insertar una película
st.sidebar.markdown("---")
st.sidebar.subheader("Nuevo filme")

with st.sidebar.form("new_movie_form"):

    new_name = st.text_input("Name")
    new_genre = st.text_input("Genre")
    new_director = st.text_input("Director")
    new_company = st.text_input("Company")

    create_movie = st.form_submit_button("Crear nuevo filme")

if create_movie:

    if new_name and new_genre and new_director and new_company:

        add_movie(
            new_name,
            new_genre,
            new_director,
            new_company
        )

        st.success("Filme creado correctamente.")
        st.rerun()

    else:
        st.warning("Completa todos los campos.")

# -------------------------
# LIBRO DE VISITAS
# -------------------------

st.sidebar.markdown("---")
st.sidebar.subheader("Libro de visitas")

with st.sidebar.form("guest_form"):

    guest_email = st.text_input("Email")
    guest_comment = st.text_area("Comentario")

    register_guest = st.form_submit_button("Registrar visita")

if register_guest:

    if guest_email and guest_comment:

        add_guest(
            guest_email,
            guest_comment
        )

        st.success("Visita registrada correctamente.")

    else:
        st.warning("Completa el email y el comentario.")


# boton para ver los comentarios
show_guests = st.sidebar.button("Ver visitas")
if show_guests:

    guests_df = load_guests()

    st.header("Libro de visitas")

    if guests_df.empty:
        st.info("No hay visitas registradas.")
    else:
        st.dataframe(
            guests_df,
            use_container_width=True
        )