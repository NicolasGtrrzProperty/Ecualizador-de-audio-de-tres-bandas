"""
Herramientas de la versión 3 del ecualizador de tres bandas.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent
QUCS_BIN = Path(r"C:\Program Files\Qucs-S\bin")
QUCS = QUCS_BIN / "qucs-s.exe"
NGSPICE = QUCS_BIN / "ngspice_con.exe"

# ---------------------------------------------------------------------------
# Valores de diseño
# ---------------------------------------------------------------------------

ORIGINAL = {"R_B": "270", "C_B": "1u", "R_M1": "150", "C_M1": "2u",
            "R_M2": "18", "C_M2": "2u", "R_A": "33", "C_A": "1u"}
AJUSTADO = {"R_B": "530.5", "C_B": "1u", "R_M1": "159.15", "C_M1": "2u",
            "R_M2": "19.89", "C_M2": "2u", "R_A": "31.83", "C_A": "1u"}
# Serie E96 (tolerancia 1 %) más próxima a cada resistencia ajustada.
COMERCIAL = {"R_B": "536", "C_B": "1u", "R_M1": "158", "C_M1": "2u",
             "R_M2": "20", "C_M2": "2u", "R_A": "31.6", "C_A": "1u"}

IGUALES = ("10k", "10k", "10k")
VARIANTES = {
    "01_original": (ORIGINAL, IGUALES, "Valores dibujados en el documento de origen"),
    "02_ajustado": (AJUSTADO, IGUALES, "Valores ajustados a 300, 500, 4 000 y 5 000 Hz"),
    "03_comercial_E96": (COMERCIAL, IGUALES, "Resistencias comerciales E96 (1 %)"),
    "04_realce_graves": (AJUSTADO, ("5k", "20k", "20k"), "Realce de graves"),
    "05_realce_medios": (AJUSTADO, ("20k", "5k", "20k"), "Realce de medios"),
    "06_realce_agudos": (AJUSTADO, ("20k", "20k", "5k"), "Realce de agudos"),
}

_SUFIJOS = {"T": 1e12, "G": 1e9, "MEG": 1e6, "K": 1e3, "M": 1e-3,
            "U": 1e-6, "N": 1e-9, "P": 1e-12, "F": 1e-15}


def valor(texto: str) -> float:
    """Convierte una magnitud de Qucs/SPICE ('1u', '10k', '1Meg') a float."""
    m = re.fullmatch(r"\s*([-+0-9.eE]+)\s*([A-Za-z]*)", texto)
    if not m:
        raise ValueError(texto)
    numero, sufijo = float(m.group(1)), m.group(2).upper()
    for clave in ("MEG", "T", "G", "K", "M", "U", "N", "P", "F"):
        if sufijo.startswith(clave):
            return numero * _SUFIJOS[clave]
    return numero


def con_unidad(texto: str, unidad: str) -> str:
    """Formato legible: '1u' -> '1 µF', '530.5' -> '530,5 Ω'."""
    v = valor(texto)
    for factor, prefijo in ((1e6, "M"), (1e3, "k"), (1, ""), (1e-3, "m"), (1e-6, "µ"), (1e-9, "n")):
        if abs(v) >= factor * 0.999:
            n = v / factor
            cifra = f"{n:.4g}".replace(".", ",")
            return f"{cifra} {prefijo}{unidad}"
    return f"{v:g} {unidad}"


# ---------------------------------------------------------------------------
# 1. Generación de esquemas Qucs-S
# ---------------------------------------------------------------------------

class Esquema:
    """Construye un archivo .sch de Qucs-S a partir de primitivas con coordenadas."""

    def __init__(self, nombre: str):
        self.nombre = nombre
        self.componentes: list[str] = []
        self.cables: list[list] = []   # [x1, y1, x2, y2, etiqueta]
        self.textos: list[str] = []
        self.puertos: list[tuple[int, int]] = []

    # -- primitivas -------------------------------------------------------
    def cable(self, *puntos, etiqueta=""):
        for (x1, y1), (x2, y2) in zip(puntos, puntos[1:]):
            self.cables.append([x1, y1, x2, y2, etiqueta])
            etiqueta = ""

    def tierra(self, x, y):
        self.componentes.append(f"  <GND * 1 {x} {y} 0 0 0 0>")
        self.puertos.append((x, y))

    def resistencia(self, nombre, x, y, r, vertical=False, texto=(-26, -44)):
        rot = 1 if vertical else 0
        self.componentes.append(
            f'  <R {nombre} 1 {x} {y} {texto[0]} {texto[1]} 0 {rot} "{r}" 1 '
            '"26.85" 0 "0.0" 0 "0.0" 0 "26.85" 0 "european" 0>')
        self._puertos_2(x, y, vertical)

    def condensador(self, nombre, x, y, c, vertical=False, texto=(-26, -44)):
        rot = 1 if vertical else 0
        self.componentes.append(
            f'  <C {nombre} 1 {x} {y} {texto[0]} {texto[1]} 0 {rot} "{c}" 1 "" 0 "neutral" 0>')
        self._puertos_2(x, y, vertical)

    def fuente_ac(self, nombre, x, y, amplitud="1 V", f="1 kHz"):
        self.componentes.append(
            f'  <Vac {nombre} 1 {x} {y} 18 -26 0 1 "{amplitud}" 1 "{f}" 1 "0" 0 "0" 0 "0" 0>')
        self._puertos_2(x, y, True)

    def opamp(self, nombre, x, y, texto=(-20, -64)):
        self.componentes.append(
            f'  <OpAmp {nombre} 1 {x} {y} {texto[0]} {texto[1]} 0 0 "1e6" 0 "15 V" 0>')
        self.puertos += [(x - 30, y - 20), (x - 30, y + 20), (x + 40, y)]

    def titulo(self, x, y, texto, tam=12):
        self.textos.append(f'  <Text {x} {y} {tam} #000000 0 "{texto}">')

    def _puertos_2(self, x, y, vertical):
        self.puertos += [(x, y - 30), (x, y + 30)] if vertical else [(x - 30, y), (x + 30, y)]

    # -- bloques del ecualizador -----------------------------------------
    def no_inversor(self, sufijo, ox, oy, rg, rf, salida, largo=50):
        """Operacional no inversor; entrada + en (ox-30, oy-20)."""
        self.opamp(f"OP_{sufijo}", ox, oy)
        self.cable((ox - 30, oy + 20), (ox - 50, oy + 20), (ox - 50, oy + 80))
        self.resistencia(f"RF_{sufijo}", ox + 10, oy + 80, rf, texto=(-24, 12))
        self.cable((ox - 50, oy + 80), (ox - 20, oy + 80))
        self.cable((ox + 40, oy + 80), (ox + 70, oy + 80), (ox + 70, oy))
        self.cable((ox + 40, oy), (ox + 70, oy))
        self.resistencia(f"RG_{sufijo}", ox - 50, oy + 150, rg, vertical=True, texto=(12, -12))
        self.cable((ox - 50, oy + 80), (ox - 50, oy + 120))
        self.cable((ox - 50, oy + 180), (ox - 50, oy + 200))
        self.tierra(ox - 50, oy + 200)
        if largo:
            self.cable((ox + 70, oy), (ox + 70 + largo, oy), etiqueta=salida)

    def filtro(self, tipo, sufijo, ox, oy, r, c, salida, largo=50, entrada=""):
        """Red RC seguida de un buffer no inversor. tipo: 'pb' o 'pa'."""
        y = oy - 20
        if tipo == "pb":
            self.resistencia(f"R_{sufijo}", ox - 150, y, r)
            self.condensador(f"C_{sufijo}", ox - 90, y + 30 + 10, c, vertical=True, texto=(-78, -12))
        else:
            self.condensador(f"C_{sufijo}", ox - 150, y, c)
            self.resistencia(f"R_{sufijo}", ox - 90, y + 30 + 10, r, vertical=True, texto=(-78, -12))
        self.cable((ox - 120, y), (ox - 30, y))
        self.cable((ox - 90, y), (ox - 90, y + 10))
        self.cable((ox - 90, y + 70), (ox - 90, y + 90))
        self.tierra(ox - 90, y + 90)
        if entrada:
            self.cable((ox - 230, y), (ox - 180, y), etiqueta=entrada)
        self.no_inversor(sufijo, ox, oy, "1Meg", "100", salida, largo)

    # -- escritura ---------------------------------------------------------
    def _dividir_cables(self):
        """Qucs-S sólo une cables por sus extremos: se parten las uniones en T."""
        puntos = set(self.puertos)
        for x1, y1, x2, y2, _ in self.cables:
            puntos |= {(x1, y1), (x2, y2)}
        cambiado = True
        while cambiado:
            cambiado = False
            for i, (x1, y1, x2, y2, et) in enumerate(self.cables):
                for (px, py) in puntos:
                    interior = ((x1 == x2 == px and min(y1, y2) < py < max(y1, y2)) or
                                (y1 == y2 == py and min(x1, x2) < px < max(x1, x2)))
                    if interior:
                        self.cables[i] = [x1, y1, px, py, et]
                        self.cables.append([px, py, x2, y2, ""])
                        cambiado = True
                        break
                if cambiado:
                    break

    def escribir(self, carpeta: Path = RAIZ) -> Path:
        self._dividir_cables()
        lineas_cables = []
        for x1, y1, x2, y2, et in self.cables:
            lineas_cables.append(f'  <{x1} {y1} {x2} {y2} "{et}" {x1 + 12} {y1 - 26} 10 "">')
        contenido = "\n".join([
            "<Qucs Schematic 26.1.1>", "<Properties>",
            "  <View=0,0,1700,1260,1,0,0>", "  <Grid=10,10,1>",
            f"  <DataSet={self.nombre}.dat>", f"  <DataDisplay={self.nombre}.dpl>",
            "  <OpenDisplay=0>", f"  <Script={self.nombre}.m>", "  <RunScript=0>",
            "  <showFrame=0>", "  <FrameText0=Title>", "  <FrameText1=Drawn By:>",
            "  <FrameText2=Date:>", "  <FrameText3=Revision:>", "</Properties>",
            "<Symbol>", "</Symbol>", "<Components>", *self.componentes,
            '  <.AC AC1 1 80 1060 0 40 0 0 "log" 1 "10 Hz" 1 "100 kHz" 1 "401" 1 "no" 0>',
            '  <.TR TR1 1 330 1060 0 40 0 0 "lin" 1 "0" 1 "10m" 1 "1001" 1 "Trapezoidal" 0 "2" 0 '
            '"10 us" 0 "1e-16" 0 "150" 0 "0.001" 0 "1 pA" 0 "1 uV" 0 "26.85" 0 "1e-3" 0 "1e-6" 0 '
            '"1" 0 "CroutLU" 0 "no" 0 "yes" 0 "0" 0>',
            "</Components>", "<Wires>", *lineas_cables, "</Wires>",
            "<Diagrams>", "</Diagrams>", "<Paintings>", *self.textos, "</Paintings>", "",
        ])
        ruta = carpeta / f"{self.nombre}.sch"
        ruta.write_text(contenido, encoding="utf-8")
        return ruta


# Coordenadas de los bloques del esquema completo (unidades de Qucs-S).
PRE = (240, 160)
GRAVES = (640, 160)
MEDIOS_1 = (640, 460)
MEDIOS_2 = (1000, 480)
AGUDOS = (640, 800)
SUMA = (1370, 520)

# Recuadros de cada etapa para las vistas ampliadas: (x0, y0, x1, y1).
VISTAS = {
    "preamplificador": (20, 60, 390, 390),
    "graves": (390, 60, 790, 385),
    "medios": (420, 395, 1170, 705),
    "agudos": (390, 700, 790, 1030),
    "sumador": (1150, 50, 1600, 840),
}


def generar_ecualizador(nombre, rc, sumador, descripcion="", carpeta: Path = RAIZ) -> Path:
    """Escribe el esquema completo: fuente, preamplificador, 3 ramas y sumador."""
    e = Esquema(nombre)
    e.titulo(20, 20, f"Ecualizador de tres bandas · {descripcion}", 14)
    # Fuente y preamplificador (K = 1 + 500/330).
    px, py = PRE
    e.titulo(40, 80, "Preamplificador")
    e.fuente_ac("VIN", 60, 220)
    e.cable((px - 30, 140), (60, 140), (60, 190), etiqueta="entrada")
    e.cable((60, 250), (60, 270))
    e.tierra(60, 270)
    e.no_inversor("PRE", px, py, "330", "500", "pre", largo=0)
    # Bus de salida del preamplificador hacia las tres ramas.
    bus = 400
    e.cable((px + 70, py), (bus, py), etiqueta="pre")
    e.cable((bus, GRAVES[1] - 20), (bus, AGUDOS[1] - 20))
    # Ramas de filtrado.
    gx, gy = GRAVES
    e.titulo(gx - 220, gy - 90, "Graves: pasa bajos")
    e.cable((bus, gy - 20), (gx - 180, gy - 20))
    e.filtro("pb", "B", gx, gy, rc["R_B"], rc["C_B"], "graves", largo=0)
    mx, my = MEDIOS_1
    e.titulo(mx - 220, my - 90, "Medios: pasa banda")
    e.cable((bus, my - 20), (mx - 180, my - 20))
    e.filtro("pa", "M1", mx, my, rc["R_M1"], rc["C_M1"], "medio_alto", largo=0)
    m2x, m2y = MEDIOS_2
    e.cable((mx + 70, my), (m2x - 180, m2y - 20), etiqueta="medio_alto")
    e.filtro("pb", "M2", m2x, m2y, rc["R_M2"], rc["C_M2"], "medios", largo=0)
    ax, ay = AGUDOS
    e.titulo(ax - 220, ay - 90, "Agudos: pasa altos")
    e.cable((bus, ay - 20), (ax - 180, ay - 20))
    e.filtro("pa", "A", ax, ay, rc["R_A"], rc["C_A"], "agudos", largo=0)
    # Sumador inversor: controles de banda (R_S*) y realimentación RF_S.
    sx, sy = SUMA
    nodo = sx - 110
    e.titulo(nodo - 90, 70, "Sumador inversor (controles)")
    salidas = [((gx + 70, gy), "graves"), ((m2x + 70, m2y), "medios"), ((ax + 70, ay), "agudos")]
    ys = [gy, m2y, ay]
    for (origen, et), y, r, suf in zip(salidas, ys, sumador, ("SB", "SM", "SA")):
        rx = nodo - 70
        if origen[1] == y:
            e.cable(origen, (rx - 30, y), etiqueta=et)
        else:
            e.cable(origen, (origen[0] + 30, origen[1]), (origen[0] + 30, y), (rx - 30, y), etiqueta=et)
        e.resistencia(f"R_{suf}", rx, y, r)
        e.cable((rx + 30, y), (nodo, y))
    e.cable((nodo, gy), (nodo, ay))
    e.opamp("OP_S", sx, sy, texto=(-10, 44))
    e.cable((nodo, sy + 20), (sx - 30, sy + 20))
    e.cable((sx - 30, sy - 20), (sx - 50, sy - 20), (sx - 50, sy - 10))
    e.tierra(sx - 50, sy - 10)
    e.resistencia("RF_S", sx + 10, 320, "10k")
    e.cable((nodo, 320), (sx - 20, 320))
    e.cable((sx + 40, 320), (sx + 80, 320), (sx + 80, sy))
    e.cable((sx + 40, sy), (sx + 80, sy))
    e.cable((sx + 80, sy), (sx + 140, sy), etiqueta="salida")
    return e.escribir(carpeta)


def generar_todos(carpeta: Path = RAIZ) -> list[Path]:
    return [generar_ecualizador(n, rc, s, d, carpeta) for n, (rc, s, d) in VARIANTES.items()]


# ---------------------------------------------------------------------------
# 2. Lectura de .sch y dibujo con estilo Qucs-S
# ---------------------------------------------------------------------------

@dataclass
class Componente:
    tipo: str
    nombre: str
    x: int
    y: int
    tx: int
    ty: int
    espejo: int
    rot: int
    props: list[tuple[str, int]] = field(default_factory=list)


def leer_sch(ruta: Path):
    texto = Path(ruta).read_text(encoding="utf-8")
    bloque = lambda tag: re.search(rf"<{tag}>\n(.*?)</{tag}>", texto, re.S).group(1)
    comps = []
    for linea in bloque("Components").splitlines():
        m = re.match(r"\s*<(\S+) (\S+) (\d) (-?\d+) (-?\d+) (-?\d+) (-?\d+) (\d) (\d)(.*)>", linea)
        if m:
            props = re.findall(r'"([^"]*)" (\d)', m.group(10))
            comps.append(Componente(m.group(1), m.group(2), *map(int, m.groups()[3:9]),
                                    [(v, int(d)) for v, d in props]))
    cables = []
    for linea in bloque("Wires").splitlines():
        m = re.match(r'\s*<(-?\d+) (-?\d+) (-?\d+) (-?\d+) "([^"]*)"', linea)
        if m:
            cables.append((*map(int, m.groups()[:4]), m.group(5)))
    textos = []
    for linea in bloque("Paintings").splitlines():
        m = re.match(r'\s*<Text (-?\d+) (-?\d+) (\d+) (#\w+) \d "([^"]*)">', linea)
        if m:
            textos.append((int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(5)))
    return comps, cables, textos


AZUL = "#000080"      # color de cables y símbolos en Qucs-S
ROJO = "#d40000"


def _rotar(puntos, rot):
    """Rotación de Qucs-S: cada paso aplica (x, y) -> (y, -x)."""
    salida = []
    for x, y in puntos:
        for _ in range(rot % 4):
            x, y = y, -x
        salida.append((x, y))
    return salida


def _simbolo(c: Componente):
    """Devuelve polilíneas (listas de puntos) y círculos del símbolo, relativos al centro."""
    lineas, circulos, signos = [], [], []
    if c.tipo == "R":
        lineas = [[(-30, 0), (-18, 0)], [(18, 0), (30, 0)],
                  [(-18, -9), (18, -9), (18, 9), (-18, 9), (-18, -9)]]
    elif c.tipo == "C":
        lineas = [[(-30, 0), (-4, 0)], [(4, 0), (30, 0)],
                  [(-4, -11), (-4, 11)], [(4, -11), (4, 11)]]
    elif c.tipo == "Vac":
        lineas = [[(-30, 0), (-12, 0)], [(12, 0), (30, 0)]]
        u = np.linspace(-7, 7, 30)
        lineas.append([(float(t), float(-5 * np.sin(np.pi * t / 7))) for t in u])
        circulos = [(0, 0, 12)]
        signos = [("+", 22, -9)]
    elif c.tipo == "OpAmp":
        lineas = [[(-30, -20), (-20, -20)], [(-30, 20), (-20, 20)], [(30, 0), (40, 0)],
                  [(-20, -35), (30, 0), (-20, 35), (-20, -35)]]
        signos = [("+", -13, -20), ("−", -13, 20)]
    elif c.tipo == "GND":
        lineas = [[(0, 0), (0, 10)], [(-11, 10), (11, 10)], [(-7, 15), (7, 15)], [(-3, 20), (3, 20)]]
    rot = 0 if c.tipo in ("GND", "OpAmp") else c.rot
    if c.tipo == "Vac":
        # El símbolo de la fuente se define horizontal; se gira como sus puertos.
        lineas = [_rotar(l, rot) for l in lineas[:2]] + [lineas[2]]
        signos = [("+", 9, -22)]
    else:
        lineas = [_rotar(l, rot) for l in lineas]
    return lineas, circulos, signos


_PROPS = {"R": ("R", "Ω"), "C": ("C", "F"), "Vac": ("U", None), "OpAmp": ("G", None)}


def _etiquetas(c: Componente):
    lineas = [c.nombre]
    if c.tipo == "R" and c.props[0][1]:
        lineas.append("R=" + con_unidad(c.props[0][0], "Ω"))
    elif c.tipo == "C" and c.props[0][1]:
        lineas.append("C=" + con_unidad(c.props[0][0], "F"))
    elif c.tipo == "Vac":
        lineas += [f"U={c.props[0][0]}", f"f={c.props[1][0]}"]
    elif c.tipo == "OpAmp" and c.props[0][1]:
        lineas.append(f"G={c.props[0][0]}")
    return lineas


def _texto(ax, *args, **kw):
    """Texto recortado al área visible (necesario en las vistas ampliadas)."""
    return ax.text(*args, clip_on=True, **kw)


def dibujar_sch(ruta: Path, vista=None, escala=1.0, titulo=None, simulaciones=True, ax=None):
    """Dibuja un .sch de Qucs-S. vista=(x0, y0, x1, y1) recorta una región."""
    import matplotlib.pyplot as plt
    from collections import Counter

    comps, cables, textos = leer_sch(ruta)
    if vista is None:
        vista = (0, 0, 1600, 1160 if simulaciones else 1030)
    x0, y0, x1, y1 = vista
    ancho, alto = x1 - x0, y1 - y0
    if ax is None:
        fig, ax = plt.subplots(figsize=(ancho / 100 * 1.05 * escala, alto / 100 * 1.05 * escala))
    else:
        fig = ax.figure
    fs = 7.6 * escala
    ax.set_xlim(x0, x1)
    ax.set_ylim(y1, y0)
    ax.set_aspect("equal")
    ax.axis("off")
    fig.patch.set_facecolor("white")
    # Rejilla de puntos, como en el editor de Qucs-S.
    gx, gy = np.meshgrid(np.arange(x0 - x0 % 20, x1, 20), np.arange(y0 - y0 % 20, y1, 20))
    ax.scatter(gx.ravel(), gy.ravel(), s=0.25 * escala, color="#c8cbd6", zorder=0, linewidths=0)

    # Cables.
    extremos = Counter()
    for xa, ya, xb, yb, et in cables:
        ax.plot([xa, xb], [ya, yb], color=AZUL, lw=1.5 * escala, solid_capstyle="round", zorder=2)
        extremos[(xa, ya)] += 1
        extremos[(xb, yb)] += 1
    # Componentes.
    recorte = vista != (0, 0, 1600, 1160 if simulaciones else 1030)
    for c in comps:
        if c.tipo.startswith("."):
            continue
        if recorte and not (x0 <= c.x <= x1 and y0 <= c.y <= y1):
            continue
        lineas, circulos, signos = _simbolo(c)
        for l in lineas:
            xs, ys = zip(*l)
            ax.plot(np.add(xs, c.x), np.add(ys, c.y), color=AZUL, lw=1.4 * escala, zorder=3,
                    solid_joinstyle="miter")
        for cx, cy, r in circulos:
            ax.add_patch(plt.Circle((c.x + cx, c.y + cy), r, fill=False, color=AZUL,
                                    lw=1.4 * escala, zorder=3))
        for s, sx, sy in signos:
            _texto(ax, c.x + sx, c.y + sy, s, color=ROJO, fontsize=fs * 1.1, ha="center",
                    va="center", zorder=4, fontweight="bold")
        if c.tipo == "GND":
            extremos[(c.x, c.y)] += 1
            continue
        if c.tipo == "OpAmp":
            puertos = [(-30, -20), (-30, 20), (40, 0)]
        else:
            puertos = _rotar([(-30, 0), (30, 0)], c.rot)
        for px, py in puertos:
            extremos[(c.x + px, c.y + py)] += 1
        for i, texto in enumerate(_etiquetas(c)):
            _texto(ax, c.x + c.tx, c.y + c.ty + i * 13, texto, fontsize=fs,
                    fontweight="bold" if i == 0 else "normal", va="top", ha="left",
                    color="#111111", zorder=5, family="DejaVu Sans")
    # Nodos: punto donde confluyen tres o más conexiones.
    for (px, py), n in extremos.items():
        if n >= 3:
            ax.add_patch(plt.Circle((px, py), 3.2, color=AZUL, zorder=4))
    # Etiquetas de nodo (wire labels).
    for xa, ya, xb, yb, et in cables:
        if not et:
            continue
        if ya == yb:
            ancla = ((xa + xb) / 2 - 20 if abs(xb - xa) > 200 else min(xa, xb) + 12, ya)
        else:
            ancla = (xa, (ya + yb) / 2)
        ax.plot([ancla[0], ancla[0] + 8], [ancla[1], ancla[1] - 14], color="#555555",
                lw=0.7 * escala, zorder=4)
        _texto(ax, ancla[0] + 9, ancla[1] - 14, et, fontsize=fs * 0.95, color="#7a0026",
                va="bottom", ha="left", zorder=6, style="italic",
                bbox=dict(boxstyle="round,pad=0.18", fc="#fff6f8", ec="#b3405f", lw=0.6))
    # Bloques de simulación.
    if simulaciones:
        for c in comps:
            if c.tipo == ".AC":
                cab, cuerpo = "simulación ac", [f"Tipo={c.props[0][0]}", f"Inicio={c.props[1][0]}",
                                               f"Fin={c.props[2][0]}", f"Puntos={c.props[3][0]}"]
            elif c.tipo == ".TR":
                cab, cuerpo = "simulación transitoria", [f"Inicio={c.props[1][0]} s",
                                                        f"Fin={c.props[2][0]}s", f"Puntos={c.props[3][0]}"]
            else:
                continue
            if not (x0 <= c.x <= x1 and y0 <= c.y <= y1):
                continue
            ax.add_patch(plt.Rectangle((c.x, c.y), 170, 26, fc="#eef0ff", ec=AZUL, lw=1.2, zorder=3))
            _texto(ax, c.x + 8, c.y + 13, cab, fontsize=fs, color=AZUL, va="center", fontweight="bold")
            for i, t in enumerate(cuerpo):
                _texto(ax, c.x + 8, c.y + 34 + i * 13, t, fontsize=fs, va="top", color="#111111")
    for tx, ty, tam, t in textos:
        if not recorte:
            _texto(ax, tx, ty, t, fontsize=tam * 0.72 * escala, va="top", ha="left",
                    color="#1b2a4a", fontweight="bold")
    if titulo:
        ax.set_title(titulo, fontsize=10 * escala, color="#1b2a4a", loc="left")
    fig.tight_layout(pad=0.3)
    return fig


# ---------------------------------------------------------------------------
# 3. Simulación con Qucs-S (netlister) + Ngspice
# ---------------------------------------------------------------------------

def simular(ruta_sch: Path, carpeta_salida: Path | None = None) -> dict:
    """Genera la netlist Ngspice con Qucs-S, la ejecuta y devuelve los vectores."""
    ruta_sch = Path(ruta_sch)
    salida = Path(carpeta_salida or ruta_sch.parent / "simulaciones")
    salida.mkdir(exist_ok=True)
    cir = salida / f"{ruta_sch.stem}.cir"
    subprocess.run([str(QUCS), "-n", "--ngspice", "-i", str(ruta_sch), "-o", str(cir)],
                   check=True, capture_output=True, timeout=120)
    netlist = cir.read_text(encoding="utf-8")

    def a_wrdata(m):
        return ("set wr_singlescale\nset wr_vecnames\noption numdgt=12\n"
                f"wrdata {ruta_sch.stem}_{m.group(1)}.txt {m.group(2)}")

    netlist = re.sub(r"write spice4qucs\.(\w+)\.plot (.*)", a_wrdata, netlist)
    cir.write_text(netlist, encoding="utf-8")
    r = subprocess.run([str(NGSPICE), "-b", cir.name], cwd=salida, capture_output=True,
                       text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(r.stdout[-2000:] + r.stderr[-2000:])
    return {"ac": _leer_wrdata(salida / f"{ruta_sch.stem}_ac1.txt", complejo=True),
            "tr": _leer_wrdata(salida / f"{ruta_sch.stem}_tr1.txt", complejo=False),
            "netlist": cir}


def _leer_wrdata(ruta: Path, complejo: bool) -> dict:
    lineas = ruta.read_text().splitlines()
    nombres = lineas[0].split()
    datos = np.array([[float(v) for v in l.split()] for l in lineas[1:] if l.strip()])
    resultado = {nombres[0]: datos[:, 0]}
    if complejo:
        for k in range(1, len(nombres), 2):
            resultado[nombres[k][2:-1]] = datos[:, k] + 1j * datos[:, k + 1]
    else:
        for k in range(1, len(nombres)):
            resultado[nombres[k][2:-1]] = datos[:, k]
    return resultado


def corte(f, h, sube: bool) -> float:
    """Frecuencia de −3 dB respecto de la ganancia de paso (interpolación logarítmica)."""
    mag = np.abs(h)
    objetivo = (mag[-1] if sube else mag[0]) / np.sqrt(2)
    d = mag - objetivo
    i = np.where(np.sign(d[:-1]) != np.sign(d[1:]))[0]
    if len(i) != 1:
        raise ValueError(f"{len(i)} cruces de −3 dB")
    i = i[0]
    t = (objetivo - mag[i]) / (mag[i + 1] - mag[i])
    return float(np.exp(np.log(f[i]) + t * (np.log(f[i + 1]) - np.log(f[i]))))


def limpiar(carpeta: Path = RAIZ):
    shutil.rmtree(carpeta / "simulaciones", ignore_errors=True)
