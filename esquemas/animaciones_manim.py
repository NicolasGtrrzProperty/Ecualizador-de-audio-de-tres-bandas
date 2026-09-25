"""
Animaciones Manim del ecualizador de tres bandas.
"""

from pathlib import Path

import numpy as np
from manim import *

SIM = Path(__file__).resolve().parent / "simulaciones"

# Paleta categórica (pasos para fondo oscuro), en orden fijo.
AZUL, NARANJA, AQUA, AMARILLO = "#3987e5", "#d95926", "#199e70", "#c98500"
TINTA, TINTA_2, EJE = "#ffffff", "#c3c2b7", "#6b6a66"
FONDO = "#1a1a19"
config.background_color = FONDO


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------

def leer(nombre, tipo="ac1"):
    lineas = (SIM / f"{nombre}_{tipo}.txt").read_text().splitlines()
    cab = lineas[0].split()
    d = np.array([[float(v) for v in l.split()] for l in lineas[1:] if l.strip()])
    datos = {cab[0]: d[:, 0]}
    if tipo == "ac1":
        for k in range(1, len(cab), 2):
            datos[cab[k][2:-1]] = d[:, k] + 1j * d[:, k + 1]
    else:
        for k in range(1, len(cab)):
            datos[cab[k][2:-1]] = d[:, k]
    return datos


def db(h):
    return 20 * np.log10(np.abs(h))


def es(x, dec=1):
    return f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")


def hz(f):
    return f"{es(f / 1000, 2)} kHz" if f >= 1000 else f"{es(f, 1)} Hz"


def corte(f, h, sube):
    mag = np.abs(h)
    obj = (mag[-1] if sube else mag[0]) / np.sqrt(2)
    d = mag - obj
    i = np.where(np.sign(d[:-1]) != np.sign(d[1:]))[0][0]
    t = (obj - mag[i]) / (mag[i + 1] - mag[i])
    return float(np.exp(np.log(f[i]) + t * (np.log(f[i + 1]) - np.log(f[i]))))


# ---------------------------------------------------------------------------
# Elementos comunes
# ---------------------------------------------------------------------------

def texto(t, tam=24, color=TINTA, **kw):
    return Text(t, font_size=tam, color=color, **kw)


def ejes_bode(y_min, y_max, paso, ancho=9.0, alto=5.0):
    ax = Axes(x_range=[1, 5, 1], y_range=[y_min, y_max, paso], x_length=ancho, y_length=alto,
              axis_config={"include_tip": False, "color": EJE, "stroke_width": 2},
              x_axis_config={"include_ticks": True}, y_axis_config={"include_ticks": True})
    rejilla = VGroup()
    for d in range(1, 5):
        for m in range(2, 10):
            x = d + np.log10(m)
            rejilla.add(Line(ax.c2p(x, y_min), ax.c2p(x, y_max), stroke_width=0.6,
                             color=EJE, stroke_opacity=0.35))
    for d in range(2, 5):
        rejilla.add(Line(ax.c2p(d, y_min), ax.c2p(d, y_max), stroke_width=1, color=EJE,
                         stroke_opacity=0.6))
    for y in np.arange(y_min, y_max + 0.1, paso):
        rejilla.add(Line(ax.c2p(1, y), ax.c2p(5, y), stroke_width=0.6, color=EJE,
                         stroke_opacity=0.35))
    etiquetas = VGroup()
    for d, t in zip(range(1, 6), ["10 Hz", "100 Hz", "1 kHz", "10 kHz", "100 kHz"]):
        etiquetas.add(texto(t, 18, TINTA_2).next_to(ax.c2p(d, y_min), DOWN, buff=0.2))
    for y in np.arange(y_min, y_max + 0.1, paso):
        etiquetas.add(texto(f"{y:g}".replace("-", "−"), 18, TINTA_2)
                      .next_to(ax.c2p(1, y), LEFT, buff=0.15))
    unidad = texto("dB", 18, TINTA_2).next_to(ax.c2p(1, y_max), UP, buff=0.15)
    return ax, VGroup(rejilla, ax, etiquetas, unidad)


def curva(ax, f, g, color, ancho=4, y_min=-1e9):
    visible = np.asarray(g) >= y_min   # se omite lo que queda bajo el eje
    x, g = np.log10(f)[visible], np.asarray(g)[visible]
    return VMobject(stroke_color=color, stroke_width=ancho).set_points_as_corners(
        [ax.c2p(a, b) for a, b in zip(x, g)])


def titulo(t, sub=None):
    grupo = VGroup(texto(t, 30, weight=BOLD))
    if sub:
        grupo.add(texto(sub, 20, TINTA_2))
    return grupo.arrange(DOWN, aligned_edge=LEFT, buff=0.12).to_corner(UL, buff=0.35)


# ---------------------------------------------------------------------------
# 1. Barrido de frecuencia sobre las tres ramas
# ---------------------------------------------------------------------------

class BarridoBandas(Scene):
    def construct(self):
        a = leer("02_ajustado")
        f = a["frequency"]
        ramas = [("Graves", db(a["graves"] / a["pre"]), AZUL),
                 ("Medios", db(a["medios"] / a["pre"]), NARANJA),
                 ("Agudos", db(a["agudos"] / a["pre"]), AQUA)]
        total = db(a["salida"] / a["entrada"])

        self.add(titulo("Barrido de frecuencia · Ngspice",
                        "Ganancia de cada rama respecto de la salida del preamplificador"))
        ax, fondo = ejes_bode(-40, 5, 5, ancho=8.6, alto=5.0)
        fondo.to_edge(LEFT, buff=0.9).shift(DOWN * 0.45)
        self.play(FadeIn(fondo), run_time=1)

        linea3 = DashedLine(ax.c2p(1, -3), ax.c2p(5, -3), color=TINTA_2, stroke_width=2)
        et3 = texto("−3 dB", 16, TINTA_2).next_to(ax.c2p(1, -3), UR, buff=0.08)
        curvas = VGroup()
        for (nombre, g, color), xl in zip(ramas, (1.35, 3.15, 4.55)):
            c = curva(ax, f, g, color, y_min=-40)
            et = texto(nombre, 22, TINTA, weight=BOLD).next_to(
                ax.c2p(xl, np.interp(xl, np.log10(f), g)), UP, buff=0.15)
            self.play(Create(c), FadeIn(et), run_time=1.3)
            curvas.add(c)
        self.play(Create(linea3), FadeIn(et3), run_time=0.6)

        lf = ValueTracker(1.0)
        cursor = always_redraw(lambda: Line(ax.c2p(lf.get_value(), -40), ax.c2p(lf.get_value(), 5),
                                            color=TINTA, stroke_width=1.5))
        puntos = VGroup(*[always_redraw(lambda g=g, color=color: Dot(
            ax.c2p(lf.get_value(), max(np.interp(lf.get_value(), np.log10(f), g), -40)),
            radius=0.08, color=color, stroke_color=FONDO, stroke_width=2))
            for _, g, color in ramas])

        def panel():
            x = lf.get_value()
            filas = [texto(f"f = {hz(10 ** x)}", 26, TINTA, weight=BOLD)]
            for nombre, g, color in ramas:
                v = np.interp(x, np.log10(f), g)
                fila = VGroup(Square(0.22, fill_color=color, fill_opacity=1, stroke_width=0),
                              texto(f"{nombre:<7}", 22, TINTA_2),
                              texto(f"{es(v)} dB".replace("-", "−"), 22, TINTA))
                fila.arrange(RIGHT, buff=0.2)
                filas.append(fila)
            filas.append(texto("Salida total", 20, TINTA_2))
            filas.append(texto(f"{es(np.interp(x, np.log10(f), total))} dB", 26, TINTA, weight=BOLD))
            return VGroup(*filas).arrange(DOWN, aligned_edge=LEFT, buff=0.22).to_edge(RIGHT, buff=0.5)

        lectura = always_redraw(panel)
        self.play(FadeIn(cursor), FadeIn(puntos), FadeIn(lectura))
        self.play(lf.animate.set_value(5.0), run_time=12, rate_func=linear)

        # Cortes simulados.
        cortes = [corte(f, a["graves"] / a["pre"], False), corte(f, a["medio_alto"] / a["pre"], True),
                  corte(f, a["medios"] / a["medio_alto"], False), corte(f, a["agudos"] / a["pre"], True)]
        marcas = VGroup(*[Dot(ax.c2p(np.log10(fc), -3), radius=0.09, color=color,
                              stroke_color=TINTA, stroke_width=2)
                          for fc, color in zip(cortes, (AZUL, NARANJA, NARANJA, AQUA))])
        filas = [texto("Cortes a −3 dB", 24, TINTA, weight=BOLD)]
        for fc, color, nombre in zip(cortes, (AZUL, NARANJA, NARANJA, AQUA),
                                     ("Graves", "Medios inferior", "Medios superior", "Agudos")):
            filas.append(VGroup(Dot(radius=0.09, color=color),
                                VGroup(texto(nombre, 18, TINTA_2), texto(hz(fc), 24, TINTA, weight=BOLD))
                                .arrange(DOWN, aligned_edge=LEFT, buff=0.06)).arrange(RIGHT, buff=0.18))
        lista = VGroup(*filas).arrange(DOWN, aligned_edge=LEFT, buff=0.24).to_edge(RIGHT, buff=0.5)
        self.play(FadeOut(cursor), FadeOut(puntos), FadeOut(lectura))
        self.play(LaggedStart(*[FadeIn(m, scale=1.6) for m in marcas], lag_ratio=0.15),
                  FadeIn(lista, shift=LEFT * 0.2), run_time=2)
        self.wait(2.5)


# ---------------------------------------------------------------------------
# 2. Corrección del filtro de graves
# ---------------------------------------------------------------------------

class CorreccionGraves(Scene):
    def construct(self):
        C = 1e-6
        K = 1 + 100 / 1e6
        o, j, e = leer("01_original"), leer("02_ajustado"), leer("03_comercial_E96")
        f = o["frequency"]

        self.add(titulo("Corrección del filtro de graves",
                        "Pasa bajos RC con C = 1 µF · meta: 300 Hz"))
        ax, fondo = ejes_bode(-30, 5, 5, ancho=8.6, alto=5.0)
        fondo.to_edge(LEFT, buff=0.9).shift(DOWN * 0.45)
        linea3 = DashedLine(ax.c2p(1, -3), ax.c2p(5, -3), color=TINTA_2, stroke_width=2)
        meta = DashedLine(ax.c2p(np.log10(300), -30), ax.c2p(np.log10(300), 5),
                          color=AMARILLO, stroke_width=2, dash_length=0.08)
        et_meta = texto("meta 300 Hz", 16, AMARILLO).next_to(ax.c2p(np.log10(300), -30), UR, buff=0.1)
        self.play(FadeIn(fondo), Create(linea3), Create(meta), FadeIn(et_meta))

        # Curva original simulada.
        c_orig = curva(ax, f, db(o["graves"] / o["pre"]), AZUL, y_min=-30)
        fc_o = corte(f, o["graves"] / o["pre"], False)
        self.play(Create(c_orig), run_time=1.5)
        m_o = Dot(ax.c2p(np.log10(fc_o), -3), radius=0.09, color=AZUL)
        t_o = texto(f"270 Ω → {hz(fc_o)}", 20, TINTA).next_to(m_o, UR, buff=0.12)
        self.play(FadeIn(m_o, scale=1.5), FadeIn(t_o))
        self.wait(0.8)

        # Barrido continuo de R_B (modelo analítico, validado con Ngspice).
        R = ValueTracker(270.0)
        fs = np.logspace(1, 5, 401)

        def h(r):
            return db(K / (1 + 2j * np.pi * fs * r * C))

        fantasma = c_orig.copy().set_stroke(opacity=0.35)
        movil = always_redraw(lambda: curva(ax, fs, h(R.get_value()), NARANJA, y_min=-30))
        punto = always_redraw(lambda: Dot(ax.c2p(np.log10(1 / (2 * np.pi * R.get_value() * C)), -3 + 20 * np.log10(K)),
                                          radius=0.09, color=NARANJA))

        def panel():
            r = R.get_value()
            return VGroup(
                texto("R_B", 22, TINTA_2),
                texto(f"{es(r, 1)} Ω", 34, TINTA, weight=BOLD),
                texto("f_c = 1 / (2π R C)", 20, TINTA_2),
                texto(hz(1 / (2 * np.pi * r * C)), 34, NARANJA, weight=BOLD),
            ).arrange(DOWN, aligned_edge=LEFT, buff=0.2).to_edge(RIGHT, buff=0.6)

        lectura = always_redraw(panel)
        self.play(FadeIn(fantasma), FadeIn(movil), FadeIn(punto), FadeIn(lectura), FadeOut(t_o))
        self.play(R.animate.set_value(530.5), run_time=6, rate_func=smooth)
        self.wait(0.5)

        # Verificación con Ngspice: ajustado y E96.
        c_aj = curva(ax, f, db(j["graves"] / j["pre"]), NARANJA, ancho=4, y_min=-30)
        fc_j = corte(f, j["graves"] / j["pre"], False)
        fc_e = corte(f, e["graves"] / e["pre"], False)
        self.remove(movil, punto)
        self.add(c_aj)
        res = VGroup(
            texto("Ngspice", 22, TINTA, weight=BOLD),
            texto(f"270 Ω → {hz(fc_o)}", 18, AZUL),
            texto(f"530,5 Ω → {hz(fc_j)}", 18, NARANJA),
            texto(f"536 Ω (E96) → {hz(fc_e)}", 18, AQUA),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.15).to_edge(RIGHT, buff=0.35).shift(DOWN * 2.3)
        self.play(FadeIn(res, shift=UP * 0.2))
        c_e = curva(ax, f, db(e["graves"] / e["pre"]), AQUA, ancho=3, y_min=-30)
        self.play(Create(c_e), run_time=1.5)
        self.wait(2.5)


# ---------------------------------------------------------------------------
# 3. Controles del sumador
# ---------------------------------------------------------------------------

AJUSTES = [
    ("Controles iguales", "02_ajustado", (10, 10, 10)),
    ("Realce de graves", "04_realce_graves", (5, 20, 20)),
    ("Realce de medios", "05_realce_medios", (20, 5, 20)),
    ("Realce de agudos", "06_realce_agudos", (20, 20, 5)),
    ("Controles iguales", "02_ajustado", (10, 10, 10)),
]


class ControlesSumador(Scene):
    def construct(self):
        self.add(titulo("Controles del sumador · Ngspice",
                        "Respuesta de la entrada a la salida · peso de cada banda = 10 kΩ / R"))
        ax, fondo = ejes_bode(-2, 16, 2, ancho=8.0, alto=4.8)
        fondo.to_edge(LEFT, buff=0.9).shift(DOWN * 0.45)
        self.play(FadeIn(fondo))

        datos = {c: leer(c) for _, c, _ in AJUSTES}
        f = datos["02_ajustado"]["frequency"]

        def curva_de(clave):
            d = datos[clave]
            return curva(ax, f, db(d["salida"] / d["entrada"]), TINTA, ancho=5)

        def lecturas(clave):
            d = datos[clave]
            g = db(d["salida"] / d["entrada"])
            grupo = VGroup()
            for fr in (100, 1000, 10000):
                v = np.interp(np.log10(fr), np.log10(f), g)
                p = ax.c2p(np.log10(fr), v)
                grupo.add(Dot(p, radius=0.07, color=TINTA),
                          texto(f"{es(v, 1)} dB", 16, TINTA).next_to(p, UP, buff=0.12))
            return grupo

        base_y = ax.c2p(1, -2)[1] + 0.2
        x0 = ax.c2p(5, 0)[0] + 1.3

        def barras(rs):
            grupo = VGroup()
            for i, (r, color, nombre) in enumerate(zip(rs, (AZUL, NARANJA, AQUA),
                                                       ("Graves", "Medios", "Agudos"))):
                peso = 10 / r
                alto = 1.5 * peso
                rect = Rectangle(width=0.55, height=alto, fill_color=color, fill_opacity=1,
                                 stroke_width=0)
                rect.move_to([x0 + i * 1.1, base_y + alto / 2, 0])
                grupo.add(VGroup(
                    rect,
                    texto(f"×{es(peso, 1)}", 18, TINTA).next_to(rect, UP, buff=0.1),
                    texto(nombre, 16, TINTA_2).move_to([x0 + i * 1.1, base_y - 0.3, 0]),
                    texto(f"{r:g} kΩ", 16, TINTA_2).move_to([x0 + i * 1.1, base_y - 0.6, 0]),
                ))
            return grupo

        nombre, clave, rs = AJUSTES[0]
        c = curva_de(clave)
        l = lecturas(clave)
        b = barras(rs)
        et = texto(nombre, 26, TINTA, weight=BOLD).move_to([x0 + 1.1, 2.1, 0])
        self.play(Create(c), FadeIn(l), FadeIn(b), FadeIn(et), run_time=2)
        self.wait(1.5)
        for nombre, clave, rs in AJUSTES[1:]:
            self.play(Transform(c, curva_de(clave)), Transform(l, lecturas(clave)),
                      Transform(b, barras(rs)),
                      Transform(et, texto(nombre, 26, TINTA, weight=BOLD).move_to([x0 + 1.1, 2.1, 0])),
                      run_time=2)
            self.wait(1.8)


# ---------------------------------------------------------------------------
# 4. Señal a 1 kHz a través del ecualizador
# ---------------------------------------------------------------------------

class SenalTransitoria(Scene):
    def construct(self):
        tr = leer("02_ajustado", "tr1")
        t = tr["time"] * 1e3
        T_FIN = 3.0
        m = t <= T_FIN + 1e-9
        cabecera = titulo("Seno de 1 V a 1 kHz · simulación transitoria de Ngspice",
                          "Controles iguales · la salida es −(graves + medios + agudos)")
        self.add(cabecera)

        filas = [
            ("Entrada y preamplificador", [("entrada", TINTA_2), ("pre", AMARILLO)], 3),
            ("Salidas de las ramas", [("graves", AZUL), ("medios", NARANJA), ("agudos", AQUA)], 2),
            ("Salida del sumador", [("salida", TINTA)], 3),
        ]
        tt = ValueTracker(0.0)
        grupos, trazos = VGroup(), []
        for i, (nombre, series, lim) in enumerate(filas):
            ax = Axes(x_range=[0, T_FIN, 0.5], y_range=[-lim, lim, lim], x_length=9.5, y_length=1.55,
                      axis_config={"include_tip": False, "color": EJE, "stroke_width": 1.5})
            ax.move_to([-0.9, 1.22 - i * 2.02, 0])
            cab = texto(nombre, 18, TINTA_2).next_to(ax, UP, buff=0.05).align_to(ax, LEFT)
            esc = VGroup(texto(f"{lim} V", 14, TINTA_2).next_to(ax.c2p(0, lim), LEFT, buff=0.1),
                         texto(f"−{lim} V", 14, TINTA_2).next_to(ax.c2p(0, -lim), LEFT, buff=0.1))
            leyenda = VGroup()
            for s, color in series:
                leyenda.add(VGroup(Line(ORIGIN, RIGHT * 0.35, color=color, stroke_width=4),
                                   texto(s, 16, TINTA_2)).arrange(RIGHT, buff=0.1))
            leyenda.arrange(DOWN, aligned_edge=LEFT, buff=0.08).next_to(ax, RIGHT, buff=0.3)
            grupos.add(VGroup(ax, cab, esc, leyenda))
            for s, color in series:
                y = tr[s][m]

                def trazo(ax=ax, y=y, color=color):
                    k = max(2, int(np.searchsorted(t[m], tt.get_value())))
                    return VMobject(stroke_color=color, stroke_width=3).set_points_as_corners(
                        [ax.c2p(a, b) for a, b in zip(t[m][:k], y[:k])])
                trazos.append(always_redraw(trazo))
        eje_t = texto("tiempo (ms)", 16, TINTA_2).next_to(grupos[-1][0].c2p(T_FIN, -3), RIGHT, buff=0.3)
        marcas = VGroup(*[texto(f"{v:g}", 14, TINTA_2).next_to(grupos[-1][0].c2p(v, -3), DOWN, buff=0.08)
                          for v in np.arange(0, T_FIN + 0.1, 0.5)])
        self.play(FadeIn(grupos), FadeIn(eje_t), FadeIn(marcas))
        self.add(*trazos)
        self.play(tt.animate.set_value(T_FIN), run_time=9, rate_func=linear)

        estable = tr["time"] > 5e-3
        amp_pre = np.max(np.abs(tr["pre"][estable]))
        amp_sal = np.max(np.abs(tr["salida"][estable]))
        nota = VGroup(
            texto(f"pre: {es(amp_pre, 2)} V  (K = 1 + 500/330 ≈ 2,52)", 18, TINTA),
            texto(f"salida: {es(amp_sal, 2)} V, invertida  ·  lejos del límite de ±15 V", 18, TINTA),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.08).next_to(cabecera[0], DOWN, buff=0.1, aligned_edge=LEFT)
        self.play(FadeOut(cabecera[1]), FadeIn(nota, shift=UP * 0.2))
        self.wait(3)
