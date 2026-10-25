"""Interfaz de chat con Gradio."""

import gradio as gr

from pipeline import answer_question, build_agent

EXAMPLES = [
    "¿Quién es el actual rector de la UCO?",
    "¿Qué empresas ofrecen maquinaria agrícola, aperos y componentes en Cataluña?",
    "¿Qué servicio puede ofrecerme la empresa Digitanimal para mi finca de olivos?",
    "¿Cuál es el clima en Córdoba España?",
    "Dime todas las empresas que ofrezcan servicio de Cuaderno Digital de Explotación en la provincia de Córdoba",
    "¿Qué empresas desarrollan software para uso de Internet of things (IoT) en la industria agroalimentaria en el País Vasco?",
    "Nombra todas las empresas que tengan soluciones tecnológicas para la ganadería a través de Drones en Andalucía",
    "¿Cuál es el proyecto mas reciente en la ETSIAM de la UCO?",
    "¿A qué empresa tecnológica puedo acudir para mejorar la productividad de mi explotación agrícola en Palma del Río?",
    "Crea un manejo integrado de plagas para Antracnosis en olivo",
]


def build_demo() -> gr.ChatInterface:
    agent, memory = build_agent()

    def chatbot(message, history):
        return answer_question(agent, memory, message)

    return gr.ChatInterface(
        fn=chatbot,
        examples=EXAMPLES,
        title="Bienvenido a tu Asistente Virtual Agrícola, ¡pregúntame sobre agricultura digital y tecnologías avanzadas!",
    )
