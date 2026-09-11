"""
EcoTrack — Clasificador ambiental de texto (PLN).

Clasifica frases en español sobre hábitos y problemas ambientales
en dos categorías:
  - Alto Impacto CO2
  - Bajo Impacto / Sostenible

Uso:
  python clasificador_ambiental.py
"""

from __future__ import annotations

import re
import sys
from typing import Iterable

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.stem import SnowballStemmer
except ImportError as exc:
    raise SystemExit(
        "Faltan dependencias. Instala con:\n  pip install scikit-learn nltk"
    ) from exc

ALTO = "Alto Impacto CO2"
BAJO = "Bajo Impacto / Sostenible"
SALIR = {"salir", "exit", "quit", "q"}


def _asegurar_recursos_nltk() -> None:
    """Descarga stopwords en español si no están en el entorno local."""
    try:
        stopwords.words("spanish")
    except LookupError:
        nltk.download("stopwords", quiet=True)


_asegurar_recursos_nltk()

STEMMER = SnowballStemmer("spanish")
STOPWORDS_ES = set(stopwords.words("spanish"))
# Negaciones y verbos de hábito: si se eliminan, el modelo pierde la señal.
STOPWORDS_ES.difference_update(
    {"no", "nunca", "sin", "ni", "nada", "como", "muy", "poco", "mucho"}
)


def tokenizar(texto: str) -> list[str]:
    """Normaliza, elimina ruido y aplica stemming en español con NLTK."""
    texto = texto.lower()
    texto = re.sub(r"[^a-záéíóúüñ\s]", " ", texto)
    tokens = [t for t in texto.split() if t and t not in STOPWORDS_ES and len(t) > 1]
    return [STEMMER.stem(token) for token in tokens]


DATASET: list[tuple[str, str]] = [
    # --- Transporte: alto impacto ---
    ("Viajo todos los días solo en mi auto de gasolina al trabajo", ALTO),
    ("Uso el coche para trayectos de tres cuadras porque no me gusta caminar", ALTO),
    ("Tomo un vuelo nacional cada fin de semana por ocio", ALTO),
    ("Dejo el motor del carro encendido mientras espero en doble fila", ALTO),
    ("Manejo una camioneta grande aunque viva en el centro de la ciudad", ALTO),
    ("Nunca uso transporte público, solo taxi o uber para todo", ALTO),
    ("Hago viajes intermunicipales en avión en vez de bus", ALTO),
    ("Acelero y freno bruscamente y consumo mucha gasolina", ALTO),
    ("Tengo dos automóviles para una persona y los uso a diario", ALTO),
    ("Prefiero el auto particular aunque exista metro cerca", ALTO),
    # --- Transporte: bajo impacto ---
    ("Voy al trabajo en bicicleta y camino las distancias cortas", BAJO),
    ("Uso el transporte público y comparto el carro cuando es necesario", BAJO),
    ("Teletrabajo tres días para evitar desplazamientos innecesarios", BAJO),
    ("Me muevo en metro, bus y a pie por la ciudad", BAJO),
    ("Comparto viajes con compañeros para reducir kilómetros en auto", BAJO),
    ("Elegí una bicicleta eléctrica en lugar de comprar un segundo carro", BAJO),
    ("Camino al supermercado del barrio en vez de manejar", BAJO),
    ("Planifico varios recados en un solo trayecto corto", BAJO),
    ("Uso tren o bus de larga distancia en vez de avión", BAJO),
    ("Mantengo el auto apagado y camino si el destino está cerca", BAJO),
    # --- Energía: alto impacto ---
    ("Dejo las luces y el aire acondicionado encendidos todo el día", ALTO),
    ("Caliento la casa a 28 grados con calefacción eléctrica constante", ALTO),
    ("Tengo electrodomésticos viejos que gastan mucha electricidad", ALTO),
    ("Ducho más de 30 minutos con agua muy caliente todos los días", ALTO),
    ("Dejo cargadores y televisores en standby las 24 horas", ALTO),
    ("Uso el secador de ropa eléctrico aunque pueda tender al sol", ALTO),
    ("Enciendo varias pantallas y luces al mismo tiempo sin necesidad", ALTO),
    ("Mi consumo eléctrico semanal es altísimo por desperdicio", ALTO),
    ("Dejo el refrigerador abierto y la nevera a temperatura extrema", ALTO),
    ("Quemo carbón o leña para calentar sin control de eficiencia", ALTO),
    # --- Energía: bajo impacto ---
    ("Apago luces y desconecto aparatos cuando no los uso", BAJO),
    ("Instalé bombillas LED y reduzco el uso del aire acondicionado", BAJO),
    ("Aprovecho la luz natural y tiendo la ropa al sol", BAJO),
    ("Tengo paneles solares y monitoreo el consumo en kWh", BAJO),
    ("Uso termostato eficiente y duchas cortas para ahorrar energía", BAJO),
    ("Compré electrodomésticos con etiqueta de eficiencia energética", BAJO),
    ("Bajo un grado la calefacción y uso ropa abrigada en casa", BAJO),
    ("Cargo el portátil de día y evito el modo espera innecesario", BAJO),
    ("Ventilo la casa por la mañana en lugar de usar aire todo el tiempo", BAJO),
    ("Cocino con olla a presión para gastar menos gas y electricidad", BAJO),
    # --- Reciclaje: alto impacto ---
    ("Tiro todos los residuos juntos sin separar ni reciclar", ALTO),
    ("Boté pilas, aceite de cocina y plástico al mismo basurero", ALTO),
    ("Uso bolsas plásticas de un solo uso y las descarto al instante", ALTO),
    ("No reciclo envases aunque el barrio tenga puntos verdes", ALTO),
    ("Quemo basura en el patio incluyendo plástico y icopor", ALTO),
    ("Compro agua embotellada todos los días y lleno la caneca de PET", ALTO),
    ("Desecho ropa y electrónicos sin buscar un centro de acopio", ALTO),
    ("Contamino el río tirando desechos y escombros", ALTO),
    ("Uso icopor y empaques no reciclables en cada comida", ALTO),
    ("Mezclo residuos orgánicos peligrosos con la basura común", ALTO),
    # --- Reciclaje: bajo impacto ---
    ("Separo orgánicos, plástico, vidrio y papel para reciclar", BAJO),
    ("Llevo las pilas y el aceite usado a un punto limpio", BAJO),
    ("Reutilizo frascos y bolsas de tela para las compras", BAJO),
    ("Composto los restos de comida y evito el relleno sanitario", BAJO),
    ("Llevo las botellas al centro de acopio del barrio", BAJO),
    ("Reparo aparatos y dono ropa en vez de tirarlos", BAJO),
    ("Evito el icopor y elijo envases retornables o reciclables", BAJO),
    ("Limpio los envases antes de depositarlos en el contenedor correcto", BAJO),
    ("Participo en jornadas de reciclaje comunitario", BAJO),
    ("Uso botella reutilizable y no compro plástico de un solo uso", BAJO),
    # --- Consumo / alimentación: alto impacto ---
    ("Como carne roja en las tres comidas todos los días de la semana", ALTO),
    ("Compro ropa nueva cada mes y descarto prendas casi sin usar", ALTO),
    ("Pido domicilio en envases desechables varias veces al día", ALTO),
    ("Desperdicio comida y echo a la basura verduras en buen estado", ALTO),
    ("Consumo productos ultraempacados importados por capricho", ALTO),
    ("Compro gadgets electrónicos que no necesito y los cambio seguido", ALTO),
    ("Mi dieta depende de carne industrial y comida ultra procesada", ALTO),
    ("Uso y tiro vasos, cubiertos y platos plásticos en cada almuerzo", ALTO),
    ("Impulso el consumismo: más compras, más empaques, más residuos", ALTO),
    ("No planifico el mercado y se me daña la comida en la nevera", ALTO),
    ("Viajo solo en auto y dejo el motor encendido", ALTO),
    ("Como carne todos los dias y no reciclo nada", ALTO),
    ("Uso el carro para todo y tiro la basura sin separar", ALTO),
    # --- Consumo / alimentación: bajo impacto ---
    ("Reduje la carne y como más legumbres, verduras y granos locales", BAJO),
    ("Compro a granel y productos de temporada del mercado campesino", BAJO),
    ("Planifico las comidas para no desperdiciar alimentos", BAJO),
    ("Hago trueque, segunda mano y reparo antes de comprar algo nuevo", BAJO),
    ("Prefiero una dieta basada en plantas varios días a la semana", BAJO),
    ("Llevo recipientes reutilizables cuando pido comida para llevar", BAJO),
    ("Consumo de forma consciente y evito compras impulsivas", BAJO),
    ("Cultivo hierbas en casa y apoyo productores locales", BAJO),
    ("Elijo productos con menos empaque y mayor durabilidad", BAJO),
    ("Practico el consumo responsable y reutilizo lo que ya tengo", BAJO),
    ("Voy en bici reciclo y como mas vegetales", BAJO),
    ("Me muevo en bicicleta reciclo envases y como verduras", BAJO),
    ("Como vegetales uso la bici y reciclo el plastico", BAJO),
    ("Habito sostenible: bici, reciclaje y alimentacion vegetal", BAJO),
]


def _textos_y_etiquetas(datos: Iterable[tuple[str, str]]) -> tuple[list[str], list[str]]:
    textos, etiquetas = zip(*datos)
    return list(textos), list(etiquetas)


def entrenar_modelo(usar_naive_bayes: bool = False) -> Pipeline:
    """
    Pipeline PLN: TF-IDF (con tokenizador NLTK) + clasificador supervisado.

    Por defecto usa LogisticRegression (estable en textos cortos).
    Pasa usar_naive_bayes=True para MultinomialNB.
    """
    textos, etiquetas = _textos_y_etiquetas(DATASET)
    clasificador = (
        MultinomialNB(alpha=0.6)
        if usar_naive_bayes
        else LogisticRegression(max_iter=2000, C=4.0, solver="lbfgs")
    )
    pipeline = Pipeline(
        [
            (
                "tfidf",
                TfidfVectorizer(
                    tokenizer=tokenizar,
                    token_pattern=None,
                    ngram_range=(1, 2),
                    min_df=1,
                ),
            ),
            ("clf", clasificador),
        ]
    )
    pipeline.fit(textos, etiquetas)
    return pipeline


MODELO = entrenar_modelo()


def clasificar(texto: str) -> dict[str, str | float]:
    """Devuelve etiqueta, confianza y una lectura breve del hábito."""
    texto = (texto or "").strip()
    if not texto:
        raise ValueError("Escribe una frase sobre un hábito ambiental.")

    etiqueta = MODELO.predict([texto])[0]
    probas = MODELO.predict_proba([texto])[0]
    clases = list(MODELO.classes_)
    confianza = float(probas[clases.index(etiqueta)])
    return {
        "texto": texto,
        "categoria": etiqueta,
        "confianza": round(confianza * 100, 1),
        "lectura": _lectura(etiqueta, confianza),
    }


def _lectura(etiqueta: str, confianza: float) -> str:
    if etiqueta == ALTO:
        return (
            "El texto describe prácticas con alta carga de emisiones o residuos. "
            "Conviene sustituir transporte motorizado, energía desperdiciada o consumo excesivo."
            if confianza >= 0.55
            else "Tendencia a alto impacto, aunque el mensaje es ambiguo. Aclara el hábito para afinar el consejo."
        )
    return (
        "El texto apunta a hábitos de menor huella: movilidad activa, eficiencia, reciclaje o consumo consciente."
        if confianza >= 0.55
        else "Tendencia sostenible, con matices. Detalla frecuencia o contexto para una mejor clasificación."
    )


def consola() -> None:
    print("=" * 64)
    print(" EcoTrack · Clasificador ambiental (PLN)")
    print(" Categorías: Alto Impacto CO2  |  Bajo Impacto / Sostenible")
    print(" Escribe una frase en español. Comandos: salir / exit / quit")
    print("=" * 64)
    print("Ejemplos:")
    print("  • Dejo el auto encendido y viajo solo todos los días")
    print("  • Voy en bici, reciclo y como más vegetales")
    print()

    while True:
        try:
            frase = input("Hábito > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nHasta luego.")
            break

        if not frase:
            continue
        if frase.lower() in SALIR:
            print("Hasta luego.")
            break

        try:
            resultado = clasificar(frase)
        except ValueError as error:
            print(f"  {error}")
            continue

        print(f"  Categoría : {resultado['categoria']}")
        print(f"  Confianza : {resultado['confianza']}%")
        print(f"  Lectura   : {resultado['lectura']}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        frase_cli = " ".join(sys.argv[1:])
        resultado = clasificar(frase_cli)
        print(f"{resultado['categoria']} ({resultado['confianza']}%)")
        print(resultado["lectura"])
    else:
        consola()
