"""
WhatsApp Webhook Server for Epigen Chatbot

This server receives webhook events from WhatsApp via Green API,
processes them using Google's Gemini AI model, and sends responses
back to the user.

The server is built with Flask and runs on Uvicorn for improved performance.
"""

import os
import json
import time
import sys
from typing import Dict, List, Any, Optional
import requests
from flask import Flask, request, jsonify
from loguru import logger
from dotenv import load_dotenv

# Load environment variables from .env file (for local development)
# This has no effect in production where environment variables are set differently
load_dotenv()

# 


# Initialize Flask application
app = Flask(__name__)

# ==================== CONFIGURATION ====================

# Get API credentials from environment variables
# These will be set as secrets in Hugging Face Spaces or other cloud environments
GREEN_API_ID = os.environ.get("GREEN_API_ID")
GREEN_API_TOKEN = os.environ.get("GREEN_API_TOKEN")
#GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
os.environ["GOOGLE_API_KEY"] = "AIzaSyA2kagts-qbRio2SxFZ_BdRa_J_eYvkA4Q"  # Set your API key here or use environment variables
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# 
logger.info(f"GREEN_API_ID={GREEN_API_ID}, GREEN_API_TOKEN={GREEN_API_TOKEN}")

# Check if required environment variables are set
if not GREEN_API_ID or not GREEN_API_TOKEN:
    logger.warning("WhatsApp API credentials not set. Webhook will not be able to send messages.")

if not GOOGLE_API_KEY:
    logger.warning("Google API key not set. AI responses will not work.")

# Configure logging
logger.remove()  # Remove default handler
logger.add(sys.stdout, level="INFO")  # Log to stdout instead of a file

# ==================== DATA STORAGE ====================

# In-memory storage for chat histories
# In a production environment, this would be replaced with a database
whatsapp_chat_histories: Dict[str, List[Dict[str, str]]] = {}

# Knowledge base content - replace with your actual content from the Streamlit app
knowledge_product = """
Te compartimos los enlaces directos de los suplementos que recomendamos. Todos tienen excelente calidad, buena absorción, no inﬂaman y están disponibles exclusivamente en Mercado Libre, para que compres con conﬁanza y seguridad.

Te enviamos varias opciones del mismo suplemento, con diferentes marcas, precios y gramajes, para que puedas elegir la que mejor se adapte a tu presupuesto y necesidades.

Te sugerimos adquirirlos desde estos enlaces, ya que son nuestras recomendaciones basadas en calidad, absorción y conﬁanza. Así te aseguras de elegir una opción efectiva y segura.

Si algún enlace no está disponible, escríbenos y con gusto te ayudamos a encontrar otra opción conﬁable.



# AL DESPERTAR (En ayunas, no rompen el ayuno)
- Desparasitante (, Loxe, vermox, una sola toma)
https://mercadolibre.com/sec/19cm8d4
https://mercadolibre.com/sec/1LMdCut

- Metil Folato (B9) 1000 mcg
https://mercadolibre.com/sec/1jqcQz1
https://mercadolibre.com/sec/2skmb7R
https://mercadolibre.com/sec/2J43yS2

- Benfotiamina o Tiamina pirofosfato(B1) 200 mg
https://mercadolibre.com/sec/2Uwf5jh
https://mercadolibre.com/sec/1pziVzB

- Metilcobalamina B12 2000 mcg
https://mercadolibre.com/sec/2J43yS2
https://mercadolibre.com/sec/2kJpVez
https://mercadolibre.com/sec/2YPysQS
https://mercadolibre.com/sec/1TkatqB

- Biotina 400 mcg
https://mercadolibre.com/sec/1cPkpFC
https://mercadolibre.com/sec/16XsDyw
https://mercadolibre.com/sec/1tqo2Nn

- Ácido pantoténico → Pantetina (B5) 250 mg
https://mercadolibre.com/sec/2dzNNBH
https://mercadolibre.com/sec/2g6TqSK

- Piridoxina B6 200 mg
https://mercadolibre.com/sec/1ypkdoX
https://mercadolibre.com/sec/2bYj2RW

- Riboﬂavina B2 100 mg)
https://mercadolibre.com/sec/1sF6rLk
https://mercadolibre.com/sec/1pp5esi

- Nicotinamida mononucleótido (B3 - Niacinamide) 500 mg Precursor NAD de 200 mg. (Posible enrojecimiento y comezón en la piel) dado el caso favor de suspenderlo y tomar un antihistamínico Loratadina o Cetirizina de 10 mg ambas. Una sola pastillas al día.
https://mercadolibre.com/sec/1npKHjw
https://mercadolibre.com/sec/22K1AUj
https://mercadolibre.com/sec/2kFVGJn
https://mercadolibre.com/sec/213bbqE
https://mercadolibre.com/sec/2rJjmcj
https://mercadolibre.com/sec/1ZFtY9y

- Litio 1000 mcg. Cabe mencionar que es un Litio natural. Que contiene el huevo y algunos mariscos.
https://mercadolibre.com/sec/1vXxrht
https://mercadolibre.com/sec/1FsP3oU
https://mercadolibre.com/sec/2PFsRJa
https://mercadolibre.com/sec/343w3zm

- Orégano 500 mg (compra solo 2 de los suplementos para hongos)
https://mercadolibre.com/sec/1uzJWkw
https://mercadolibre.com/sec/1339T9T
https://mercadolibre.com/sec/2FzNJRW

- Echinacea purpurea 500 mg (compra solo 2 de los suplementos para hongos)
https://mercadolibre.com/sec/24Hwj93
https://mercadolibre.com/sec/159NQ8C (5 gotas)

- Candida (compra solo 2 de los suplementos para hongos)
https://mercadolibre.com/sec/2KaBBnm
https://mercadolibre.com/sec/2uDREX2

- Chlorella cápsulas 1000 mg (radiación)
https://mercadolibre.com/sec/2hYrayP
https://mercadolibre.com/sec/19xY5ew
https://mercadolibre.com/sec/1Z4VXXJ (una cucharada)

- Cucharada de vinagre de manzana en ayunas (bacterias)
https://mercadolibre.com/sec/2Ctaico
https://mercadolibre.com/sec/1wCqJHS

- Curcuma en capsulas 300 mg (bacterias)
https://mercadolibre.com/sec/2J6r2S8
https://mercadolibre.com/sec/2wTJfJv
https://mercadolibre.com/sec/1zXBvn6

- Suplementos de ajo negro 500mg (parásitos, esporas, señales viales, señales post virales)
https://mercadolibre.com/sec/1DorM5F
https://mercadolibre.com/sec/191GCBf
https://mercadolibre.com/sec/1egGDJW

- Suplemento capsulas jengibre 500 mg (señales virales y post virales)
https://mercadolibre.com/sec/1aoPico
https://mercadolibre.com/sec/11bDdkM

- Semillas de calabaza (parásitos) comer un puño.
https://mercadolibre.com/sec/27EGgwj
https://mercadolibre.com/sec/2on1mMq
https://mercadolibre.com/sec/1usfPtw

- Cucharada de aceite de coco (parásitos)
https://mercadolibre.com/sec/1qYqYTw
https://mercadolibre.com/sec/1V41EH5
https://mercadolibre.com/sec/1fWgcxE

- Manganeso 10 mg
https://mercadolibre.com/sec/31ENxw7
https://mercadolibre.com/sec/28dFJT5
https://mercadolibre.com/sec/2q5kf82



# Después de tu primer alimento
- Omega 3 de 1000 mg con mayor concentración de EPA:
https://mercadolibre.com/sec/33D7Fsc
https://mercadolibre.com/sec/2NsSYzn
https://mercadolibre.com/sec/2yPMzMY
https://mercadolibre.com/sec/2nJXv4g
https://mercadolibre.com/sec/2uYTiW4

- Omega 3 de 1000 mg con mayor concentración de DHA:
https://mercadolibre.com/sec/2yPMzMY
https://mercadolibre.com/sec/2watQBh
https://mercadolibre.com/sec/2J6p2x1
https://mercadolibre.com/sec/2uYTiW4

- Omega 3 de 1000 mg con mayor concentración de ALA:
https://mercadolibre.com/sec/2cAVtTa

- Vitamina A1 2000 mcg
No hay enlaces disponibles aun

- Co enzima Q10 200 mg
https://mercadolibre.com/sec/1qRdEvi
https://mercadolibre.com/sec/1Qk5Swr
https://mercadolibre.com/sec/12tCKEj

- Vitamina E 268 mg o 400 UI Tomar por 2 meses
https://mercadolibre.com/sec/1TRQLG4
https://mercadolibre.com/sec/28tLrpt
https://mercadolibre.com/sec/1fvLEib

- Vitamina D3 5000 iU
https://mercadolibre.com/sec/19aKKqZ
https://mercadolibre.com/sec/2tv564R Tomar 2 capsulas
https://mercadolibre.com/sec/1aSeBcbTomar 2 capsulas

- Vitamina K1 100 mcg
https://mercadolibre.com/sec/1F4sKJ8

- Vitamina K2 100 mcg
https://mercadolibre.com/sec/1GQ9Wxo
https://mercadolibre.com/sec/1Vk2msM
https://mercadolibre.com/sec/2PT9LmH

- Betaína HCI con pepsin de 600 mg.
https://mercadolibre.com/sec/2iiN885
https://mercadolibre.com/sec/2WopC4z
https://mercadolibre.com/sec/1Cr2FyM

- Molibdeno 250 mcg
https://mercadolibre.com/sec/31ENxw7
https://mercadolibre.com/sec/2XsnSdt
https://mercadolibre.com/sec/188ZToY

- L-Fenilalanina 500 mg
https://mercadolibre.com/sec/1Mdc8iw
https://mercadolibre.com/sec/2fLaPYF
https://mercadolibre.com/sec/13FJ346
https://mercadolibre.com/sec/1NA7nfw

- L-Isoleucina (lo consigues como BCAA en cápsula sin azúcar)
https://mercadolibre.com/sec/1XEMidj
https://mercadolibre.com/sec/16wVZuL

- Acido alfa lipoico 500 mg
https://mercadolibre.com/sec/2Y2sFsD
https://mercadolibre.com/sec/1FG7Qkx
https://mercadolibre.com/sec/1eXVvGm
https://mercadolibre.com/sec/2TuGLg8
https://mercadolibre.com/sec/2RhYcsS
https://mercadolibre.com/sec/2ck8Vu4

- L- Carnitina 500 mg
https://mercadolibre.com/sec/1GyhFvk
https://mercadolibre.com/sec/1Qonf6U
https://mercadolibre.com/sec/2C7USF6
https://mercadolibre.com/sec/1rksCKs

- L-Serina de 500 mg
https://mercadolibre.com/sec/28SKmXY
https://mercadolibre.com/sec/22H5tu9
https://mercadolibre.com/sec/2fB9EBX

- L-Ácido Glutámico 500 mg
https://mercadolibre.com/sec/2D6dfgi

- L-Arginina 500 mg
https://mercadolibre.com/sec/1UUvxLN
https://mercadolibre.com/sec/2xrkE1Y
https://mercadolibre.com/sec/2iVt3Lu

- L-Glicina 500 mg
https://mercadolibre.com/sec/1wXLxJW (una cucharada pequeña)
https://mercadolibre.com/sec/1T7HR6g (una cucharas pequeña)

- L-Glutamina 1000 mg
https://mercadolibre.com/sec/13Si6XT
https://mercadolibre.com/sec/13Si6XT
https://mercadolibre.com/sec/2wBvb6q (una cucharada pequeña)
https://mercadolibre.com/sec/1K2bSE6 (una cucharada pequeña)
https://mercadolibre.com/sec/2s4bakK

- L-Citrulina 500 mg
https://mercadolibre.com/sec/1zaWvBb
https://mercadolibre.com/sec/1zqY9od (una cuchara pequeña)
https://mercadolibre.com/sec/2K7C776
https://mercadolibre.com/sec/2iZ3iUV
https://mercadolibre.com/sec/1gtrYtP

- L-Beta Alanina 1000 MG 
https://mercadolibre.com/sec/2qytFou (una cucharada pequeña)
https://mercadolibre.com/sec/12WeYKq (una cucharada pequeña)
https://mercadolibre.com/sec/2E7ziiu (una cucharas pequeña)

- L-Metionina 1000 mg
https://mercadolibre.com/sec/16jNPLm
https://mercadolibre.com/sec/1aCLLhJ
https://mercadolibre.com/sec/16jNPLm
https://mercadolibre.com/sec/2xU9KU8

- L-Cisteina 500 mg
https://mercadolibre.com/sec/13GtyCx
https://mercadolibre.com/sec/2rZ2dMw
https://mercadolibre.com/sec/1mYJbtN
https://mercadolibre.com/sec/2bCo9uJ
https://mercadolibre.com/sec/1rfTXpA

- L-Cistina 500 mg
No hay enlaces disponibles aun

- L-Lisina 1000 mg
https://mercadolibre.com/sec/1MEqpmV
https://mercadolibre.com/sec/1Pv3PTX
https://mercadolibre.com/sec/1Wm4fgZ
https://mercadolibre.com/sec/2JAxEK9
https://mercadolibre.com/sec/1xgD8rP

- L-Ácido Aspártico 1000m g
https://mercadolibre.com/sec/1FarAxe
https://mercadolibre.com/sec/1mPQk2W
https://mercadolibre.com/sec/2AHHLJN

- L-Treonina 500 mg
https://mercadolibre.com/sec/16wVZuL
https://mercadolibre.com/sec/1Sk86H4

- L-Prolina 1000 mg
https://mercadolibre.com/sec/2sCscEf
https://mercadolibre.com/sec/1pndazE

- L-Valina 500 mg (lo consigues como BCAA en cápsula sin azúcar)
https://mercadolibre.com/sec/16wVZuL
https://mercadolibre.com/sec/2Z7xj6X (una cucharada pequeña)
https://mercadolibre.com/sec/2rV7Q8u (una cucharada pequeña)

- L-Histidina 500 mg
https://mercadolibre.com/sec/2BuPsVi
https://mercadolibre.com/sec/31XYbaR
https://mercadolibre.com/sec/2gkPtNE

- L-Taurina de 500 mg
https://mercadolibre.com/sec/1VyjgnG
https://mercadolibre.com/sec/2mGzTvV
https://mercadolibre.com/sec/1T1T7ZD

- L-Leucina 500 mg

https://mercadolibre.com/sec/2ieMjzy (una medida )
https://mercadolibre.com/sec/16wVZuL (una medida )
https://mercadolibre.com/sec/23jk4cj
https://mercadolibre.com/sec/2QEGX1r (una cucharada)

- L-Tirosina 500 mg
https://mercadolibre.com/sec/1Y51cZJ
https://mercadolibre.com/sec/1JAoe3x
https://mercadolibre.com/sec/2MMphPp
https://mercadolibre.com/sec/2CDCutj
https://mercadolibre.com/sec/1BLSzaT

- L-Ornitina 500 mg
https://mercadolibre.com/sec/2MqNVPP
https://mercadolibre.com/sec/2MaSxSP
https://mercadolibre.com/sec/1e1p767
https://mercadolibre.com/sec/1ZPCTjR

- L-Asparagina 500 mg (comer minimo 3 veces a la semana espárragos)
No hay enlaces disponibles aun

- L-Carnosina 500 mg
https://mercadolibre.com/sec/1Juz1Mp
https://mercadolibre.com/sec/2Xog7tR
https://mercadolibre.com/sec/2ZH5f5g



# DESPUÉS DE TU COMIDA
- Vitamina C liposomada sin azúcar de 500 mg
https://mercadolibre.com/sec/1n8wz4F tomar la mitad
https://mercadolibre.com/sec/2NNqBKm
https://mercadolibre.com/sec/2NNqBKm

- Superóxido de dismutasa (sod) de 200 mg
https://mercadolibre.com/sec/2uRnbbH
https://mercadolibre.com/sec/2ZmAW8a

- Yodo 150 mcg 3 ( 3 gotas)
https://mercadolibre.com/sec/32PANji
https://mercadolibre.com/sec/2aPgBHN
https://mercadolibre.com/sec/2PzPcAw

- Sodio (usar ﬂor de sal o sal céltica con todos tus alimentos)
https://mercadolibre.com/sec/1XPbkT4
https://mercadolibre.com/sec/1gukwrZ
https://mercadolibre.com/sec/1oz5wK5
https://mercadolibre.com/sec/2cHJ8q1
https://mercadolibre.com/sec/2E6N6C6

- Cobre 2 mg
https://mercadolibre.com/sec/1Uz8ZYo
https://mercadolibre.com/sec/2TUuVrm
https://mercadolibre.com/sec/1b3My5a

- Silicio 500 mg
https://mercadolibre.com/sec/2fprwb3
https://mercadolibre.com/sec/1jG17d2 (media cucharad pequeña)

- Fósforo 200 mg
https://mercadolibre.com/sec/2B7Y8bb
https://mercadolibre.com/sec/2jtVCnj
https://mercadolibre.com/sec/1CtG7Uk

- Calcio 600 mg (Solo si realiza actividad física de fuerza , caminar no cuenta)
https://mercadolibre.com/sec/1Utzh7w
https://mercadolibre.com/sec/2rJBG7m
https://mercadolibre.com/sec/2w9rKkh
https://mercadolibre.com/sec/28Rr3BC

- Hierro 10 mg.
https://mercadolibre.com/sec/1N2fGFi Tomar la mitad
https://mercadolibre.com/sec/2a2Ccg4 tomar la mitad
https://mercadolibre.com/sec/1GBZL8X tomar la mitad

- Azufre (MSM) 1000 mg
https://mercadolibre.com/sec/2weJVbt
https://mercadolibre.com/sec/1DBFFyi

- Sulforafano glucosinolato (DIM) 300 MG
https://mercadolibre.com/sec/2irXMZP
https://mercadolibre.com/sec/32xLbYo
https://mercadolibre.com/sec/1XmRJ33

- Cromo 200 mcg
https://mercadolibre.com/sec/29ZmXLE
https://mercadolibre.com/sec/1eFLB61
https://mercadolibre.com/sec/1JVBDLT

- Contrato de Potasio 1000 mg
https://mercadolibre.com/sec/2WvXU8u
https://mercadolibre.com/sec/1opvU6y
https://mercadolibre.com/sec/1wqmf1k



# UNA HORA ANTES DE DORMIR
- Selenio 200 mcg
https://mercadolibre.com/sec/1cPzkF2
https://mercadolibre.com/sec/2gygZE3
https://mercadolibre.com/sec/131tFC9

- Zinc 50 mg
https://mercadolibre.com/sec/343x6EX
https://mercadolibre.com/sec/1MjmVEf
https://mercadolibre.com/sec/2MZoe9H

- Boro 3 mg
https://mercadolibre.com/sec/2ZKudWz
https://mercadolibre.com/sec/1b7CvDd
https://mercadolibre.com/sec/1t7C4ji
https://mercadolibre.com/sec/1yjQ1E7
https://mercadolibre.com/sec/1yywvjj

- Magnesio tipo glicinato de 350 mg
https://mercadolibre.com/sec/2wncKNQ
https://mercadolibre.com/sec/1vBmz42
https://mercadolibre.com/sec/12nwJUB

- Valeriana 1000mg (Sueño)
https://mercadolibre.com/sec/1qbcanX
https://mercadolibre.com/sec/11Zk4A9
https://mercadolibre.com/sec/1BE7ZV2

- Ñame Salvaje 1000 mg(menopausia)
https://mercadolibre.com/sec/2SMWE8e

- Vitex 1000 mg (menopausia)
https://mercadolibre.com/sec/2obUhxe
https://mercadolibre.com/sec/1tSEfXF
https://mercadolibre.com/sec/2nx2w5W

- Carotenoides: 20 mg
https://mercadolibre.com/sec/2KsUKcq
https://mercadolibre.com/sec/1n1k4Eb
https://mercadolibre.com/sec/2Z2CKVR

- Antocianinas 400 mg
https://mercadolibre.com/sec/2gFVLnc
https://mercadolibre.com/sec/1Aqxo19
https://mercadolibre.com/sec/2jnLRPp

- Polifenoles 500 mg
https://mercadolibre.com/sec/2aszygF
https://mercadolibre.com/sec/2GU8Utk
https://mercadolibre.com/sec/2CaojCV

- Flavonoides 500 mg
https://mercadolibre.com/sec/1gn21Bm
https://mercadolibre.com/sec/16oBrV5
https://mercadolibre.com/sec/2YBbYxf

- Glutation 500 mg (Metales pesados y quimicos-Hidrocarburos)
https://mercadolibre.com/sec/1svrdne
https://mercadolibre.com/sec/2yhkvuK
https://mercadolibre.com/sec/1VekGx1
https://mercadolibre.com/sec/2V2DPPp
https://mercadolibre.com/sec/2VkSerY
https://mercadolibre.com/sec/2y44bwx

- L-Triptófano 500 mg
https://mercadolibre.com/sec/2iZDjYE
https://mercadolibre.com/sec/2WS7DTM
https://mercadolibre.com/sec/1vgN1iU
https://mercadolibre.com/sec/1w9PGFZ
https://mercadolibre.com/sec/2iZgH1i

- Inositol 500 mg
https://mercadolibre.com/sec/2iZDjYE
https://mercadolibre.com/sec/16aY71E
https://mercadolibre.com/sec/2HviS2u
https://mercadolibre.com/sec/13GjVz1

- Fitoestrógenos (Dong Quai) 500 mg
https://mercadolibre.com/sec/1yuW3KS
https://mercadolibre.com/sec/1wFgJfu
https://mercadolibre.com/sec/2DBhad2

- Probiótico con la cepa Biﬁdobacterium cualquiera de esta cepa (Hongos)
https://mercadolibre.com/sec/1CVCr3h
https://mercadolibre.com/sec/2GPdKjX
https://mercadolibre.com/sec/1kcrDnD

- Probiótico con la cepa Saccharomyce Boulardii (Bacterias)
https://mercadolibre.com/sec/2CrCyYM
https://mercadolibre.com/sec/2Jtn5tb
https://mercadolibre.com/sec/1EqbAUT

- Ashwagandha
No hay opciones disponibles aun

###
Si los encuentras en diferentes gramajes, si es pastilla la puedes partir, si es cápsula la puedes partir y diluir en
agua.

Estos suplementos son 100% naturales y no tienen efectos secundarios y no dañan tu riñón, tu hígado o algún
otro órgano.

Este protocolo de suplementación natural está fundamentado y cimentado en tu test Epigenético. Dicho conocimiento y
tecnologia esta desarrollada y respaldada por https://www.epixlife.com
y https://www.cell-wellbeing.es del cual formamos parte de su equipo como Epigen. Para más información da click en el enlace.
Tecnología Certiﬁcada : El S-Drive cumple plenamente con la guía 1300013 de la FDA (UCM429674).

Estas recomendaciones están basadas en evidencia científica y tienen como objetivo mejorar el estilo de vida. No constituyen una
consulta médica ni un diagnóstico. Epigen se deslinda de cualquier mal uso de la información proporcionada. Se recomienda
siempre consultar a un profesional de la salud para cualquier diagnóstico o tratamiento específico.
"""

knowledge_content = """
# Datos de Epigen
- WhatsApp: 5544918977
- Direccion: Avenida de los Insurgentes 601, 03810 Col. Nápoles, CDMX, CP:03100
- Sitio Web: https://epigen.mx/
- Facebook: https://www.facebook.com/share/19twC6nMZH/?mibextid=LQQJ4d
- Instagram: https://www.instagram.com/epigen.mx?igsh=MTVkbXphaDI5dnl4ZA==
- Publico objetivo: Hombre o mujer que busque mejorar su salud y estilo de vida con pruebas químicas y de ADN preventivas. El cliente ya cuenta con tendencia sintomatica.
- Propuesta de valor: 
  1. Toma el control de tus hábitos
  2. Domina tu cuerpo
  3. Sé el dueño de tu propio cuerpo, domina tus padecimientos 
  4. Entender tu cuerpo y conocerlo
  5. Modificar la expresión de tus genes  
  6. Prevenir enfermedades 
  7. Checar tu estado de salud 
 

    
# Productos:
## Test de prevención diabetes e infartos al corazón. 
Enlace a video explicativo: https://drive.google.com/file/d/18PZYmAfmWiG3U8uvSnvKC1xlTzqO6q9Z/view?usp=sharing

Que contiene: 

1. Prueba rápida (HbA1c) hemoglobina glicosilada 
Provistos:
- Instructivo de uso
- Prueba rápida en cartucho
- Gotero
- Vial con reactivo de corrimiento (Buffer)
- Tubo capilar
- Lanceta (punción capilar)
- Almohadilla con alcohol (punción capilar)

2. Prueba rápida de NT-proBNP:
Prueba rápida en cartucho
- Gotero
- Reactivo de corrimiento (Buffer)
- Instructivo de uso.

¿Qué es la prueba NT-proBNP?
Es un análisis de sangre que mide una proteína liberada por el corazón cuando está bajo estrés. Ayuda a detectar y monitorear problemas como insuficiencia cardíaca.

Beneficios de la prueba NT-proBNP:
- Detecta problemas temprano, incluso antes de síntomas.
- Aclara síntomas como falta de aire o cansancio, diferenciando problemas cardíacos de otros.
- Monitorea tratamientos para enfermedades cardíacas.

¿Qué es HbA1c?
Esta prueba es como un reporte trimestral de tus niveles de azúcar en sangre. No mide lo que comiste ayer, sino cómo ha estado tu azúcar en los últimos 2-3 meses.

¿Por qué es útil la prueba HbA1c?
- Detectar y controlar la diabetes: Si tienes diabetes o estás en riesgo, nos ayuda saber si tu estilo de vida está funcionando.
- Prevenir complicaciones: Conocer tu HbA1c puede ayudarte a evitar problemas en el corazón, los riñones y los ojos, ya que el azúcar elevado puede dañarlos con el tiempo.

Las 2 pruebas (HbA1c y NT-proBNP) no son invasivas y te dan tranquilidad sobre la salud de tu corazón y que tu glucosa está trabajando bien. ¡Una gran inversión para Si tienes antecedentes familiares de problemas cardíacos, diabetes síntomas como cansancio inexplicable, mucha sed, manchas oscuras en el cuello o axilas, o simplemente quieres asegurarte de que tu corazón y glucosa está en buen estado. ¡Invierte en tu tranquilidad y bienestar!



## Test antiinflamatorio-segundo cerebro - intestino.
Enlace a video explicativo: https://drive.google.com/file/d/1PzO3sOkxQ4hQOkpzs3BgD2eTDb2feDlR/view?usp=sharing

¿Qué contiene?
1. Prueba rápida de Calprotectina (heces) es un inmunoensayo cromatográfico de flujo lateral para la detección cualitativa de calprotectina en muestras de heces. 
Contiene:
- Prueba rápida en cartucho
- Instructivo de uso
- Tubo colector con reactivo de corrimiento
- Gotero

2. Prueba rapida H. Pylori:
- Material para venopunción
- Centrifuga
- Lanceta (punción capilar)
- Almohadilla con alcohol

¿Qué es la calprotectina?
Es una prueba que mide la inflamación en tu intestino. Es como un detector de problemas que nos dice si hay algo fuera de lo normal en tu sistema digestivo, como enfermedades inflamatorias (por ejemplo, colitis o enfermedad de Crohn).

¿Qué es el H. pylori?
El H. pylori es una bacteria que puede vivir en tu estómago y causar molestias como gastritis, úlceras e incluso aumentar el riesgo de otros problemas más graves si no se trata. Esta prueba detecta si la bacteria está presente.

¿Qué tienen en común estas pruebas (calprotectina y H. pylori)?
Ambas nos ayudan a identificar por qué tienes síntomas como dolor abdominal, diarrea, hinchazón, o acidez. Juntas, nos dan un panorama completo:
Calprotectina: Indica si hay inflamación en el intestino.
H. pylori: Busca si la bacteria está afectando tu estómago.

¿Qué beneficios obtienes al hacerte ambas pruebas?
- Diagnóstico temprano: Detectamos problemas como inflamación o infecciones antes de que empeoren.
- Alivio de síntomas: Puedes mejorar tu calidad de vida al resolver molestias digestivas como dolor, acidez o diarrea.
- Prevención de complicaciones: Evitas que pequeñas molestias se conviertan en enfermedades más graves, como úlceras o problemas intestinales crónicos.

Si tienes molestias digestivas, estas pruebas son tu mejor aliado para entender qué pasa y solucionarlo antes de que sea más serio. ¡Con ellas, damos un paso firme hacia un sistema digestivo saludable y una mejor calidad de vida sin inflamación!



## Test perdida de peso (Mujer) 
Enlace a video explicativo: https://drive.google.com/file/d/1lPxL9qlaZ-knZnTlSDPxBpXti1q_S8OB/view?usp=sharing

Que contiene?
1. La prueba TSH (sangre/suero/plasma) es un inmunoensayo cromatográfico rápido para la detección cualitativa de la hormona estimulante de la tiroides (TSH) en sangre, suero o plasma humano. 
Contiene:
- Cartucho de prueba
- Gotero
- Buffer
- Manual de instrucciones.

2. Prueba rápida de Calprotectina (heces) es un inmunoensayo cromatográfico de flujo lateral para la detección cualitativa de calprotectina en muestras de heces. 
Contiene:
- Prueba rápida en cartucho
- Instructivo de uso
- Tubo colector con reactivo de corrimiento
- Gotero

Estas dos pruebas son como detectives que nos ayudan a entender si hay algo detrás de la dificultad para bajar de peso o de otros síntomas que puedas estar sintiendo. Te explico cómo funcionan y cómo pueden ayudarte:

¿Qué es la prueba de calprotectina?
Esta prueba analiza una proteína en tus heces para detectar si hay inflamación en tu intestino. ¿Por qué importa para la pérdida de peso? Porque una inflamación intestinal puede dificultar la absorción de nutrientes, causar molestias digestivas como hinchazón o diarrea, y afectar tu metabolismo.

¿Qué es la prueba de TSH?
Es una prueba de sangre que mide cómo está funcionando tu tiroides, una glándula clave para el control del peso. Si tienes una tiroides lenta (hipotiroidismo), tu metabolismo puede estar más lento, lo que hace que perder peso sea más difícil, además de causar cansancio y retención de líquidos.

¿Cómo se complementan estas pruebas (calprotectina y TSH)?
Juntas nos dan un panorama completo de dos aspectos clave para tu salud y peso:
- Inflamación intestinal (calprotectina): Nos ayuda a detectar si hay problemas digestivos que están afectando tu bienestar y peso.
- Función metabólica (TSH): Nos dice si tu tiroides está funcionando correctamente para mantener tu metabolismo activo.

¿Qué beneficios obtienes al hacer estas pruebas?
- Descubrir la raíz del problema: Si estás batallando con el peso o sientes síntomas como hinchazón, fatiga o cambios en el apetito, estas pruebas nos dicen si el problema viene del intestino, la tiroides o ambos.
- Plan personalizado: Con los resultados, podemos ajustar tu alimentación.
- Optimizar tu metabolismo: Si tu tiroides no está funcionando bien, podemos corregirlo y activar tu metabolismo para que perder peso sea más fácil.
- Mejorar tu digestión: Resolver problemas intestinales no solo mejora tu bienestar general, sino que también ayuda a que tu cuerpo aproveche mejor los nutrientes y elimine toxinas de manera efectiva.

Estas pruebas son como un mapa que nos guía para identificar y resolver cualquier obstáculo que esté afectando tu peso y tu salud en general. ¡Con ellas, damos el primer paso hacia una vida más saludable y un peso equilibrado!



## Test perdida de peso (Hombre)
¿Qué contiene?
1. Prueba rápida de Calprotectina (heces) es un inmunoensayo cromatográfico de flujo lateral para la detección cualitativa de calprotectina en muestras de heces. 
Contiene:
- Prueba rápida en cartucho
- Instructivo de uso
- Tubo colector con reactivo de corrimiento
- Gotero

2. La prueba rápida Micro albumina cualitativa (Orina) es un inmunoensayo cromatográfico de flujo lateral para la detección cualitativa de albúmina en muestras de orina. 
Contiene:
- Prueba rápida en cartucho
- Instructivo de uso
- Gotero

Inflamacion en tus intestino. Esto es importante porque una inflamación puede causar problemas digestivos, como hinchazón, diarrea o mala absorción de nutrientes, lo que puede dificultar la pérdida de peso y afectar tu bienestar.

¿Qué es la prueba de albúmina en orina?
Esta prueba evalúa si hay presencia de albúmina, una proteína que normalmente no debería estar en la orina. Si aparece, puede ser una señal de que tus riñones están bajo estrés o no están funcionando al 100%. Los riñones sanos son esenciales para eliminar toxinas y líquidos, procesos importantes en el control del peso.

¿Cómo se complementan estas pruebas (calprotectina y albúmina en orina)?
Ambas trabajan juntas para darnos una visión de dos aspectos importantes:
- Digestión y absorción (calprotectina): Si hay inflamación intestinal, puede afectar cómo tu cuerpo procesa los alimentos y cómo se siente en general.
- Eliminación y función renal (albúmina en orina): Detectar problemas en los riñones asegura que tu cuerpo esté eliminando toxinas y líquidos de forma efectiva, algo fundamental para un metabolismo saludable.

¿Qué beneficios obtienes al realizarte estas pruebas?
- Identificar obstáculos invisibles: Si tienes problemas para perder peso, síntomas digestivos o hinchazón, estas pruebas nos ayudan a detectar si el problema viene del intestino o de los riñones.
- Prevenir complicaciones: Detectar problemas intestinales o renales a tiempo evita complicaciones más serias que puedan afectar tu salud.
- Plan de acción personalizado: Con los resultados, podemos ajustar tu dieta, tratamiento o hábitos para mejorar la salud intestinal y renal, ayudando a que pierdas peso de manera más efectiva.
- Mejor calidad de vida: Resolver estos problemas te hará sentir con más energía, menos hinchado y con un sistema que funcione mejor.

Resumen: Estas pruebas son como un chequeo profundo de tu sistema digestivo y renal, dos pilares fundamentales para una pérdida de peso saludable. ¡Son el primer paso para entender qué está pasando y ayudarte a alcanzar tus metas de manera segura y efectiva!



## Test Epigenetico
Enlace a video explicativo: https://drive.google.com/file/d/1PFxFPTXlYNpgLMWB_wFJMl78lS9YPloH/view?usp=sharing

Modifica la expresión de tus genes hasta en un 97% con nuestro test epigenético. Gracias a toda la información que nos da personalizada de ti. Es un traje a la medida para tus necesidades en base a:
- Vitaminas ideales para ti en las dosis correctas reforzando el sistema inmunológico-intestino y cardiaco.
- Renovación y ajuste de tu microbiota intestinal
- Desintoxicación de metales pesados- químicos hidrocarburos- Radiación
- Que alimentos no van contigo y cual si por 90 días.




# Como realizar las pruebas:

## Paso a paso del proceso del paciente durante su tratamiento solo kits:
- Prevención diabetes-Infartos
Video de como realizar la prueba: https://drive.google.com/file/d/18PZYmAfmWiG3U8uvSnvKC1xlTzqO6q9Z/view?usp=sharing
- Inflamación-Intestino
Video de como realizar la prueba: https://drive.google.com/file/d/11wlB1UtxLNy8m1DnT8tUUYuydf42ODXZ/view?usp=sharing
- Bajar de peso 
Video de como realizar la prueba: https://drive.google.com/file/d/1jZWQHGNv90Xrm-fdAHo769bN1ORg7jRE/view?usp=sharing

Paso 1: Le llega el paquete - Realiza la prueba. Manda sus resultados en foto al whatsapp

Paso 2: Confirmamos de recibido y comentar que en 24 horas o menos estar recibiendo la interpretación de sus resultados así como la consulta grabada por una IA donde sera mi voz explicando los pasos a seguir. Así como trazar metas y objetivos a 2 meses. Ya que es un proyecto a 2 meses.

Paso 3: Recepción de documentos-Video. Que mandaremos? 
- Plan de alimentos de acuerdo a su padecimiento.
- Suplementación natural así como adaptógenos adecuados a su padecimiento. 
- Protocolos adecuados a su padecimiento y de acuerdo al cuestionario contestado previamente como: Mejorar el sueño, desintoxicacion y ayuno. 
- Lo añadiremos a nuestra comunidad donde daremos conferencias e información valiosa de salud, alimentación entre otras.

Paso 4: Contacto por whatsapp en todo momento. Pero al mes nosotros contactaremos par ver avances y ajuste a sus planes si se requiere.

Paso 5: A los 2 meses de haber terminado su proyecto. Lo contactamos. Retroalimentación y resultados
Recomendamos un nuevo test para validar resultados así como tendrá beneficios de descuento por ser cliente


## Paso a paso del proceso del paciente durante su tratamiento solo kits:
- Epigenético
Video de como realizar la prueba: https://drive.google.com/file/d/1TQJlHe3_wnFCU-LxaWbQTGxiMr_dXDb1/view?usp=sharing

Paso 1: Le llega el paquete - Se quita el cabello y manda sus resultados. Nosotros estaremos mandando pinzas para quitar el cabello, bolsa para colocar el cabello y la guía para que mande de regreso el cabello a nuestra oficina.

Paso 2: Cuando tengamos el paquete de cabello Confirmamos de recibido y comentar que en 24 horas o menos estar recibiendo.
La Interpretación de sus resultados así como la consulta grabada por una IA donde sera mi voz explicando los pasos a seguir. Así como trazar metas y objetivos a 3 meses. Ya que es un proyecto a 3 meses ya que el ciclo celular dura 3 meses.

Paso 3: Recepción de documentos- Video. Que mandaremos?
- Plan de alimentos de acuerdo a su padecimiento.
- Suplementación de acuerdo al estudio de epigenetica. 
- Protocolos de acuerdo al test como microbiota, desintoxicación, mejora el sueño. 
- Lo añadiremos a nuestra comunidad donde daremos conferencias e información valiosa de salud, alimentación entre otras.

Paso 4: Contacto por whatsapp en todo momento. Pero al mes y medio nosotros lo contactaremos par ver avances y ajuste a sus planes si se requiere.

Paso 5: A los 3 meses de haber terminado su proyecto. Lo contactamos. Retroalimentación y resultados
Recomendamos un nuevo test para validar resultados así como tendrá beneficios de descuento por ser cliente


# Seguimiento para despues de hacerse los tests 
Despues de que el paciente realiza un test epigenético inicial:
1. Se aplica un cuestionario de evaluación específico según el objetivo
2. Se implementa un régimen de ayuno intermitente
3. Se asignan suplementos según los resultados del test y preguntas del cuestionario
4. Se asigna un plan de alimentación específico (Fase 1, Fase 1.0, etc. o Fase 27 para intestino) - La duración del protocolo es de dos meses
5. Se recomienda un segundo test para validar resultados y ajustar el plan

## Cuestionario general para despues de un test
Preguntas para cualquier paciente haya salido positivo o negativo en el test.
- ¿Qué objetivo y metas tienes al realizar este test?
- ¿Tomas alguna medicina actualmente ?
- ¿Cuál tomás y en qué momento del día lo consumes?
- ¿Tienes buena calidad de sueño ?
- ¿Cuántas horas duermes?
- ¿Te cuesta trabajo generar sueño, estás despertando en la noche o ambas?
- ¿Tienes energía durante el día del 1 al 5 siendo el cinco mayor que tanta energía tienes?
- ¿Te despiertas cansado o la energía se va terminando en el día?
- ¿Te sientes irritable de mal humor en el día a día con poca tolerancia?
- ¿Tienes buen dinamismo mental, lucidez o se te están olvidando las cosas, te cuesta trabajo concentrarte, niebla mental?
- ¿Estrés laboral o personal del 1 al 5 cuánto tienes, siendo el 5 el mayor qué tanto estrés tienes?
- ¿A qué hora es tu último alimento del día ?
- ¿A qué hora es tu primer alimento del día?
- ¿Que seria mas facil para ti dejar de cenar o desayunar?
- ¿Con que te sentiras mas agusto, un menú con opciones o una lista de alimentos?
- ¿Que tan adicto estas a la azúcares del 1 al 5 siendo el cinco el mayor, carbohidratos(pan, pasta, tortilla, arroz, avena, frijoles, harinas, frutas, dulces, papitas, refrescos?
- ¿Tienes buena digestión?
- ¿Te inflamas de tu estómago regularmente?
- ¿Cómo son tus heces fecales? (tiritas delgadas, bolitas, pedaceria, líquido, troncos grueso normales como una salchicha)
- ¿Cuántas veces comes en el día contando snack o entrecomidas?
- ¿Consideras que masticas bien la comida?
- ¿Qué más has intentado para bajar de peso?
- ¿Por qué abandonan las dietas?
- ¿Cómo podríamos hacer este proceso más facil para ti?
- ¿Descríbeme un desayuno, comida, snack o entre comidas y cena típico en ti?
- ¿Practicas alguna actividad física regularmente?
- ¿Notas que se está oscureciendo alguna parte de tu cuerpo como cuello, entrepiernas, axilas?
- ¿Fumas?
- ¿Si fumas, cuántos cigarros al día?
- ¿Consumes alcohol?
- ¿Realizas alguna actividad física?
- ¿Algún dato o tema que consideres relevante que yo sepa y quieras comentarme?


## Ayuno (indicar siempre a todos)
- Ayuno mínimo de 14 horas máximo 16 horas.
- Es mejor dejar de cenar que desayunar pero adaptamos al paciente a su estilo de vida y sensaciones.
- Se tiene que hacer minimo 6 dias a la semana
- Siempre se debe romper el ayuno con lo que está marcado en tu plan de nutrición.
- Durante el ayuno solo se puede tomar, te verde, cafe negro y agua, cualquier de los 3 sin leche, ningun tipo de azucar, splenda etc.
- Los suplementos indicados no rompen el ayuno.



## Suplementos

## Test de prevención diabetes e infartos al corazón. 
Indicaciones solo para cuando el paciente se haya hecho el Test de prevención diabetes e infartos al corazón. 

Suplementos de prevencion de diabetes o para diabeticos
- Berberina 500 mg por la noche
- Inositol 500 mg por la noche
- L- Taurina 500 mg en ayunas
- Cromo 200 mcg en ayunas

Suplementos de prevencion de infartos al corazón 
- L-Arginina 1000 mg
- Coenzima Q10 200 mg
- Omega 3 mayor concentración de EPA Y DHA 1000 mg

Proyecto de nutricion
- El plan de alimentación que va es: Fase 1 (menú) o Fase 1.000 (lista de alimentos)
  Enlace a Fase 1: https://drive.google.com/file/d/19GsDV1AQ0eX7MnM9qsQ69d1r9QX5yWcj/view?usp=sharing
  Enlace a Fase 1.000: https://drive.google.com/file/d/1mvisfBqF2_D01ZAHFzu1ToHpBbTwm5OB/view?usp=sharing
- El plan Fase 1.0 (menú) o Fase 1.00 (lista de alimentos) va si los veo muy adictos al azúcar y carbohidratos.
  Enlace a Fase 1.0: https://drive.google.com/file/d/1Rh_Feo1n95nbJZFRy2Tnz9W4inUaEzmK/view?usp=sharing
  Enlace a Fase 1.00: https://drive.google.com/file/d/1ffQhwQ-APqrVZjlC1IAORyk-AWafm_0v/view?usp=sharing


Detox general
- Jugos de desintoxicación: 
1. Tomar un vaso con jugo de apio realizado en extractor con poquita curcuma en polvo, un diente de jengibre molido y el jugo de un limón. Te lo tomas para romper tu ayuno. A los 30 min tomar en vaso con dos cucharadas soperas de aceite de oliva con el jugo de un limón. Esto por un mes 
2. Un manojo de cilantro (hacer presión para que quepa bastante) • 5 cm de jengibre fresco • 4 limones (sin cáscara) • Un pepino grandes (sin cáscara ) • 1 manzana verde, retirar las semillas. Todo en la licuadora con agua al gusto. Esto en ayunas por un mes
- Glutation 500 mg en la noche
- Complejo b en ayunas

Suplementos solo si menciona en el cuestionario que duerme mal:
- Magnesio tipo glicinato 400 mg por la noche
- Ashwagandha 500 mg por la noche



## Test antiinflamatorio-segundo cerebro - intestino. 
Indicaciones solo para cuando el paciente se haya hecho el Test antiinflamatorio-segundo cerebro - intestino. 

Suplementos de prevencion 
- L-Glutamina 500 mg en ayunas
- Probiótico con la cepa Saccharomyce Boulardii en la noche
- Probiótico con la cepa Bifidobacterium en la noche
- Betaína 600 mg en ayunas

Suplementos solo si sale positivo en alguna o todas las pruebas (calprotectina y H. pylori)
- Desparasitante (oxal, Loxe, vermox, una sola toma)
- Cucharada de vinagre de manzana en ayunas (bacterias)
- Curcuma en capsulas 300 mg (bacterias)
- Suplementos de ajo negro 500mg (parásitos, esporas, señales viales, señales post virales)
- Suplemento capsulas jengibre 500 mg (señales virales y post virales)
- Semillas de calabaza (parásitos) comer un puño.
- Cucharada de aceite de coco (parásitos)
- Orégano 500 mg

Proyecto de nutricion
- Primer mes: Fase 27 
  Enlace a Fase 27: https://drive.google.com/file/d/1ZFIrn0U-oWk45UxAyV44tD2SnPhzISqe/view?usp=sharing
- Segundo mes: Fase 1 (menú) o Fase 1.000 (lista de alimentos)
  Enlace a Fase 1: https://drive.google.com/file/d/19GsDV1AQ0eX7MnM9qsQ69d1r9QX5yWcj/view?usp=sharing
  Enlace a fase 1.000: https://drive.google.com/file/d/1mvisfBqF2_D01ZAHFzu1ToHpBbTwm5OB/view?usp=sharing

Detox general
- Jugos de desintoxicación: 
1. Tomar un vaso con jugo de apio realizado en extractor con poquita curcuma en polvo, un diente de jengibre molido y el jugo de un limón. Te lo tomas para romper tu ayuno. A los 30 min tomar en vaso con dos cucharadas soperas de aceite de oliva con el jugo de un limón. Esto por un mes 
2. Un manojo de cilantro (hacer presión para que quepa bastante) • 5 cm de jengibre fresco • 4 limones (sin cáscara) • Un pepino grandes (sin cáscara ) • 1 manzana verde, retirar las semillas. Todo en la licuadora con agua al gusto. Esto en ayunas por un mes
- Glutation 500 mg en la noche
- Complejo b en ayunas

Suplementos solo si menciona en el cuestionario que duerme mal:
- Magnesio tipo glicinato 400 mg por la noche
- Ashwagandha 500 mg por la noche










### Test perdida de peso (Mujer)  
Indicaciones solo para cuando el paciente se haya hecho el Test perdida de peso (Mujer)  

Suplementos de prevencion
- BCAA, sin azúcar después de tu primer alimento.
- Cromo 200 mcg en ayunas
- Acido alfa lipoico 500 mg

Proyecto de nutricion
- El plan de alimentación que va es: Fase 1 (menú) o Fase 1.000 (lista de alimentos)
  Enlace a Fase 1: https://drive.google.com/file/d/19GsDV1AQ0eX7MnM9qsQ69d1r9QX5yWcj/view?usp=sharing
  Enlace a Fase 1.000: https://drive.google.com/file/d/1mvisfBqF2_D01ZAHFzu1ToHpBbTwm5OB/view?usp=sharing
- El plan Fase 1.0 (menú) o Fase 1.00 (lista de alimentos) va si los veo muy adictos al azúcar y carbohidratos.
  Enlace a Fase 1.0: https://drive.google.com/file/d/1Rh_Feo1n95nbJZFRy2Tnz9W4inUaEzmK/view?usp=sharing
  Enlace a Fase 1.00: https://drive.google.com/file/d/1ffQhwQ-APqrVZjlC1IAORyk-AWafm_0v/view?usp=sharing

Detox general
- Jugos de desintoxicación: 
1. Tomar un vaso con jugo de apio realizado en extractor con poquita curcuma en polvo, un diente de jengibre molido y el jugo de un limón. Te lo tomas para romper tu ayuno. A los 30 min tomar en vaso con dos cucharadas soperas de aceite de oliva con el jugo de un limón. Esto por un mes 
2. Un manojo de cilantro (hacer presión para que quepa bastante) • 5 cm de jengibre fresco • 4 limones (sin cáscara) • Un pepino grandes (sin cáscara ) • 1 manzana verde, retirar las semillas. Todo en la licuadora con agua al gusto. Esto en ayunas por un mes
- Glutation 500 mg en la noche
- Complejo b en ayunas

Sumplementos solo si sale positivo en la prueba de TSH:
- Yodo liquido 3 gotas
- Selenio 200 mcg
- L-Tirosina 500 mg
- Vitamina d 5000 IU

Suplementos solo si menciona en el cuestionario que duerme mal:
- Magnesio tipo glicinato 400 mg por la noche
- Ashwagandha 500 mg por la noche


## Test perdida de peso (Hombre)
Indicaciones solo para cuando el paciente se haya hecho el Test perdida de peso (Hombre)  

Suplementos de prevencion
- BCAA, sin azúcar después de tu primer alimento.
- Cromo 200 mcg en ayunas
- Acido alfa lipoico 500 mg

Proyecto de nutricion
- El plan de alimentación que va es: Fase 1 (menú) o Fase 1.000 (lista de alimentos)
  Enlace a Fase 1: https://drive.google.com/file/d/19GsDV1AQ0eX7MnM9qsQ69d1r9QX5yWcj/view?usp=sharing
  Enlace a Fase 1.000: https://drive.google.com/file/d/1mvisfBqF2_D01ZAHFzu1ToHpBbTwm5OB/view?usp=sharing
- El plan Fase 1.0 (menú) o Fase 1.00 (lista de alimentos) va si los veo muy adictos al azúcar y carbohidratos.
  Enlace a Fase 1.0: https://drive.google.com/file/d/1Rh_Feo1n95nbJZFRy2Tnz9W4inUaEzmK/view?usp=sharing
  Enlace a Fase 1.00: https://drive.google.com/file/d/1ffQhwQ-APqrVZjlC1IAORyk-AWafm_0v/view?usp=sharing

Detox general
- Jugos de desintoxicación: 
1. Tomar un vaso con jugo de apio realizado en extractor con poquita curcuma en polvo, un diente de jengibre molido y el jugo de un limón. Te lo tomas para romper tu ayuno. A los 30 min tomar en vaso con dos cucharadas soperas de aceite de oliva con el jugo de un limón. Esto por un mes 
2. Un manojo de cilantro (hacer presión para que quepa bastante) • 5 cm de jengibre fresco • 4 limones (sin cáscara) • Un pepino grandes (sin cáscara ) • 1 manzana verde, retirar las semillas. Todo en la licuadora con agua al gusto. Esto en ayunas por un mes
- Glutation 500 mg en la noche
- Complejo b en ayunas

Sumplementos solo si sale positivo en la prueba albúmina
- Liverheal de Adapto Heal

Suplementos solo si menciona en el cuestionario que duerme mal:
- Magnesio tipo glicinato 400 mg por la noche
- Ashwagandha 500 mg por la noche




## Test Epigenetico
Indicaciones solo para cuando el paciente se haya hecho el Test Epigenetico

Suplementos recomendados
Revisar el documento y consumir los recomendados por el test: https://drive.google.com/file/d/1iAQZPe7HlLnuXQiRkUoRYHXPSfm9Tmt-/view?usp=sharing

Proyecto de nutricion
- El plan de alimentación que va es: Fase 1 (menú) o Fase 1.000 (lista de alimentos)
  Enlace a Fase 1: https://drive.google.com/file/d/19GsDV1AQ0eX7MnM9qsQ69d1r9QX5yWcj/view?usp=sharing
  Enlace a Fase 1.000: https://drive.google.com/file/d/1mvisfBqF2_D01ZAHFzu1ToHpBbTwm5OB/view?usp=sharing
- El plan Fase 1.0 (menú) o Fase 1.00 (lista de alimentos) va si los veo muy adictos al azúcar y carbohidratos.
  Enlace a Fase 1.0: https://drive.google.com/file/d/1Rh_Feo1n95nbJZFRy2Tnz9W4inUaEzmK/view?usp=sharing
  Enlace a Fase 1.00: https://drive.google.com/file/d/1ffQhwQ-APqrVZjlC1IAORyk-AWafm_0v/view?usp=sharing

Detox general
- Jugos de desintoxicación: 
1. Tomar un vaso con jugo de apio realizado en extractor con poquita curcuma en polvo, un diente de jengibre molido y el jugo de un limón. Te lo tomas para romper tu ayuno. A los 30 min tomar en vaso con dos cucharadas soperas de aceite de oliva con el jugo de un limón. Esto por un mes 
2. Un manojo de cilantro (hacer presión para que quepa bastante) • 5 cm de jengibre fresco • 4 limones (sin cáscara) • Un pepino grandes (sin cáscara ) • 1 manzana verde, retirar las semillas. Todo en la licuadora con agua al gusto. Esto en ayunas por un mes
- Glutation 500 mg en la noche

Suplementos solo si menciona en el cuestionario que duerme mal:
- Magnesio tipo glicinato 400 mg por la noche
- Ashwagandha 500 mg por la noche



"""


# ==================== ROUTE HANDLERS ====================

@app.route('/', methods=['GET'])
def home():
    """
    Home route to confirm the server is running.
    
    This endpoint is useful for:
    1. Checking if the server is alive
    2. Basic health monitoring
    3. Browser-based verification
    
    Returns:
        JSON response with status message
    """
    return jsonify({
        "status": "online",
        "message": "Epigen WhatsApp webhook server is running",
        "version": "1.0.0"
    }), 200

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    """
    Main webhook endpoint for WhatsApp.
    
    Handles two types of requests:
    - GET: Used by Green API to verify the webhook URL
    - POST: Receives incoming message notifications
    
    Returns:
        JSON response indicating success or error
    """
    # Log the request method
    logger.info(f"Webhook called with method: {request.method}")
    
    # Handle webhook verification (GET request)
    if request.method == 'GET':
        logger.info("Received webhook verification request")
        return jsonify({"status": "webhook is active"}), 200
    
    # Handle incoming webhook events (POST request)
    try:
        # Log the raw request data
        raw_data = request.get_data(as_text=True)
        logger.info(f"Raw webhook data: {raw_data}")
        
        # Get the JSON data from the request
        data = request.get_json()
        logger.info(f"Parsed webhook data: {json.dumps(data)}")
        
        # Process incoming messages
        if data.get("typeWebhook") == "incomingMessageReceived":
            message_data = data.get("messageData", {})
            
            # Handle text messages
            if message_data.get("typeMessage") == "textMessage":
                sender = data["senderData"]["sender"].split("@")[0]  # Get phone number
                message_text = message_data["textMessageData"]["textMessage"]
                logger.info(f"Received message from {sender}: {message_text}")
                
                # Process the message and get a response
                ai_response = process_message(sender, message_text)
                logger.info(f"Generated response: {ai_response}")
                
                # Send the response back to the user
                send_result = send_whatsapp_message(sender, ai_response)
                logger.info(f"Send result: {send_result}")
                
            # Handle voice messages (future enhancement)
            elif message_data.get("typeMessage") == "audioMessage":
                sender = data["senderData"]["sender"].split("@")[0]
                logger.info(f"Received audio message from {sender}")
                
                # Currently we don't process audio, so just send a default response
                send_whatsapp_message(
                    sender, 
                    "Recibí tu mensaje de voz, pero actualmente solo puedo procesar mensajes de texto."
                )
        
        return jsonify({"status": "message processed"}), 200
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/test_echo/<message>', methods=['GET'])
def test_echo(message):
    """Test route to echo a message back"""
    return jsonify({
        "status": "success", 
        "message": f"You said: {message}"
    }), 200

@app.route('/test_send/<phone>/<message>', methods=['GET'])
def test_send(phone, message):
    """Test route to manually send a WhatsApp message"""
    try:
        result = send_whatsapp_message(phone, message)
        return jsonify({
            "status": "message sent",
            "result": result,
            "to": phone,
            "message": message
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# ==================== MESSAGE PROCESSING ====================

def process_message(sender: str, message_text: str) -> str:
    """
    Process a message and generate an AI response.
    
    This function:
    1. Initializes chat history for new users
    2. Adds the user message to history
    3. Generates an AI response
    4. Adds the response to history
    
    Args:
        sender (str): The phone number of the sender
        message_text (str): The content of the message
        
    Returns:
        str: The AI-generated response
    """
    try:
        # Initialize chat history for new users
        if sender not in whatsapp_chat_histories:
            whatsapp_chat_histories[sender] = [
                {"role": "assistant", "content": "¡Hola! Soy el asistente de Epigen. ¿Cómo puedo ayudarte hoy? 🧬"}
            ]
            logger.info(f"Initialized new chat history for {sender}")
        
        # Add user message to history
        whatsapp_chat_histories[sender].append({"role": "user", "content": message_text})
        
        # Generate AI response with retry mechanism
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Generate response using AI
                response = generate_ai_response(
                    whatsapp_chat_histories[sender], 
                    message_text
                )
                
                # Add AI response to history
                whatsapp_chat_histories[sender].append({"role": "assistant", "content": response})
                logger.info(f"Generated response for {sender}: {response[:50]}...")
                
                return response
            
            except Exception as e:
                logger.error(f"Attempt {attempt+1}/{max_retries} failed: {str(e)}")
                if attempt == max_retries - 1:  # Last attempt
                    raise
                time.sleep(1)  # Wait before retrying
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return "Lo siento, tuve un problema procesando tu mensaje. Por favor intenta de nuevo."

def generate_ai_response(chat_history: List[Dict[str, str]], user_message: str) -> str:
    """
    Generate a response using the Google Gemini model.
    
    This function:
    1. Configures the Gemini API
    2. Formats the conversation history
    3. Adds the system message with knowledge base
    4. Generates and returns the response
    
    Args:
        chat_history (List[Dict[str, str]]): The conversation history
        user_message (str): The latest user message
        
    Returns:
        str: The generated AI response
    """
    # Import the Gemini API library
    # We import here to avoid loading it unless needed
    import google.generativeai as genai
    
    # Configure the Gemini API
    genai.configure(api_key=GOOGLE_API_KEY)
    
    # Set up the model with appropriate parameters
    generation_config = {
        "temperature": 0.7,        # Controls randomness (0.0 = deterministic, 1.0 = creative)
        "top_p": 0.95,             # Nucleus sampling parameter
        "top_k": 0,                # Limits vocabulary to top K tokens
        "max_output_tokens": 1000, # Maximum length of response
    }
    
    # Safety settings to prevent harmful or inappropriate content
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
    ]
    
    # Initialize the generative model
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",  # Using the more efficient model for faster responses
        generation_config=generation_config,
        safety_settings=safety_settings,
    )
    
    # Format the conversation history for Gemini
    # Gemini uses "user" and "model" roles instead of "user" and "assistant"
    formatted_history = []
    for message in chat_history:
        role = "user" if message["role"] == "user" else "model"
        formatted_history.append({"role": role, "parts": [message["content"]]})
    
    # Add system message with knowledge base
    # This provides context about Epigen to inform the AI's responses
#    system_message = (
#        "Eres un agente conversacional de IA experto en epigenética y en los productos de Epigen. "
#        "Usa la siguiente información para responder preguntas sobre Epigen:\n\n" + knowledge_content
#    )


#    system_message = (
#    "Eres un agente conversacional de IA experto en epigenética y en los productos de Epigen. "
#    "Usa la siguiente información para responder preguntas sobre Epigen:\n\n"
#    f"{knowledge_content}\n\n"
#    "IMPORTANTE: Si el usuario está interesado en un test específico, brindar los enlaces a Drive "
#    "con información sobre el test.\n"
#    "IMPORTANTE: Si el usuario menciona que ya se ha hecho un test, preguntar si tiene los resultados. "
#    "Si ya tiene los resultados, hacer las preguntas del 'Cuestionario general para despues de un test' "
#    "a modo de conversación hasta que conteste todas las preguntas de forma individual. "
#    "No te detengas a menos que el usuario lo indique. Una vez que has terminado o el usuario ya no "
#    "quiere contestar las preguntas, ofrécele los suplementos correspondientes a su test."
#    )

    system_message = f"""
    # 0. IDENTIDAD
    Tu nombre es *Noa*, asistente personal entrenada por Diego. Eres cálida,
    clara y cercana. Respondes siempre en el idioma del usuario.
    
    # 1. BIENVENIDA  (envía como DOS textos seguidos, cada uno <400 car.)
    1️⃣ Hola! Soy Noa, tu asistente personal entrenada por Diego. Sí, soy un
    robot… ¡pero nada frío ni cuadrado! 😅 He escuchado dos años de consultas,
    charlas y hasta sus chistes. 🧠💛
    2️⃣ Disponible 24/7 para resolver dudas, elegir suplementos o descifrar
    datos de tu test, sin drama. ✨ No reemplazo a Diego ni a tu médico; soy tu
    copiloto. ¿Lista? Escríbeme cuando quieras. 💬
    
    # 2. FORMATO WHATSAPP
    - 1–3 líneas por mensaje (<400 car.).
    - *Negritas* y _cursivas_ para resaltar. Emoji opcional, máx. 1 🙂
    - Guiones para listas.
    - URLs completas (“https://…”) en su propia línea → toque único para abrir.
    - No uses formato Markdown de enlaces (nada de [ ]( )). Escribe la URL tal cual.
      • Si necesitas dar >1 URL, reparte en varios mensajes (máx. 3 enlaces por
        mensaje, cada uno en línea aparte).
    - Primer consejo de salud → añade _«Esto no sustituye la opinión de un
      profesional de la salud.»_
    - Primer dato personal recibido → añade _«Tus datos se manejan de forma
      confidencial y segura.»_
    
    # 3. FUENTES
    {knowledge_content}
    
    {knowledge_product}
    
    # 4. CUÁNDO MENCIONAR EPIGEN
    Solo cuando el usuario:
    - Pregunte por un test o suplemento Epigen, o
    - Indique que ya completó un test.
    
    # 5. FLUJO PARA TESTS
    1. Pregunta si tiene resultados y cómo prefiere enviarlos (PDF o foto).
    2. Si los comparte, aplica el “Cuestionario general para después de un test”,
       una pregunta por mensaje; detente cuando lo pida.
       • Si hay varios tests, pídele elegir uno primero.
    3. Al cerrar la dinámica (o si lo solicita) describe suplementos ligados al
       test, sin precios salvo que pregunte.
    
    # 6. PREGUNTAS DE COMPRA
    Cuando el usuario diga “¿Dónde lo compro?” o similar:
    1. Busca el suplemento en `knowledge_product`.
    2. Envía un mensaje con nombre y breve nota de calidad.
    3. Luego reparte las URLs (máx. 3 por mensaje) en líneas aparte, por ej.:
       🔗 https://mercadolibre.com/sec/19cm8d4
       🔗 https://mercadolibre.com/sec/1LMdCut
    4. Cierra con: “Si algún enlace no está disponible, avísame y te paso otra
       opción.”
    
    # 7. FUERA DE DOMINIO
    Si preguntan algo ajeno a salud/epigenética:
    _«No manejo ese tema, pero puedo sugerirte fuentes confiables.»_
    
    # 8. LÍMITES
    - Sin diagnósticos definitivos.
    - Cero marketing invasivo.
    """
    formatted_history.insert(0, {"role": "model", "parts": [system_message]})
    
    # Generate response
    chat = model.start_chat(history=formatted_history)
    response = chat.send_message(user_message)
    
    return response.text

# ==================== WHATSAPP INTEGRATION ====================

def send_whatsapp_message(recipient: str, message: str) -> Optional[Dict[str, Any]]:
    """
    Send a message back to the user via WhatsApp.
    
    Uses Green API to send messages to WhatsApp users.
    
    Args:
        recipient (str): The phone number to send the message to
        message (str): The content of the message
        
    Returns:
        Optional[Dict[str, Any]]: The response from the Green API, or None if failed
    """
    # Construct the URL for the Green API endpoint
    url = f"https://api.green-api.com/waInstance{GREEN_API_ID}/sendMessage/{GREEN_API_TOKEN}"
    
    # Prepare the payload with the recipient and message
    payload = {
        "chatId": f"{recipient}@c.us",  # Format required by WhatsApp
        "message": message
    }
    
    try:
        # Send the request to Green API
        response = requests.post(url, json=payload)
        response_data = response.json()
        
        # Log the result
        if response.status_code == 200 and response_data.get("idMessage"):
            logger.info(f"Message sent to {recipient}: {message[:50]}...")
        else:
            logger.error(f"Error sending message: {response_data}")
        
        return response_data
    
    except Exception as e:
        logger.error(f"Exception when sending message: {str(e)}")
        return None

# ==================== UTILITY ROUTES ====================

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring services.
    
    Returns detailed information about the server's status,
    including environment configuration and service availability.
    
    Returns:
        JSON response with health information
    """
    # Check Green API connectivity
    green_api_status = "configured" if GREEN_API_ID and GREEN_API_TOKEN else "not configured"
    
    # Check Google API connectivity
    google_api_status = "configured" if GOOGLE_API_KEY else "not configured"
    
    # Return comprehensive health status
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "green_api": green_api_status,
            "google_ai": google_api_status
        },
        "active_chats": len(whatsapp_chat_histories)
    }), 200

# ==================== SERVER STARTUP ====================

# This block only runs when executing this file directly
# In production, Uvicorn will import and run the Flask app object
if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 7860))
    
    # Log the server startup
    logger.info(f"Starting server on port {port}")
    
    # Run the server using Uvicorn
    # Using WSGI interface since Flask is a WSGI application
    uvicorn.run("app:app", host="0.0.0.0", port=port, interface="wsgi")
