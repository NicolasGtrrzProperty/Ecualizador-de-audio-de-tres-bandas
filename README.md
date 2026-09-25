# Ecualizador de audio de tres bandas

Repositorio para ilustrar un ecualizador de tres bandas (Grave, medio y agudo) para una señal de audio, mediante circuitos activos RC y amplificadores operacionales.

Los circuitos electrónicos se generan con esquemas de **[Qucs-S](https://github.com/ra3xdh/qucs_s)**, se simulan con **[Ngspice](https://github.com/ra3xdh/qucs_s)**, se dibujan con **[Python](https://www.python.org/downloads/)** y se modelan con **[Manim](https://github.com/ManimCommunity/manim)**.

## Resumen

Se diseño un ecualizador activo que comprende señales con frecuencias de **300 Hz** (límite superior de graves), **500 - 4.000 Hz** (medios) y **5.000 Hz** (límite inferior de agudos).

<div align="center">
  <table>
    <tr>
      <th>Banda</th>
      <th>Tipo de filtro</th>
      <th>Frecuencias objetivo (−3 dB)</th>
    </tr>
    <tr>
      <td>Graves</td>
      <td>Pasa bajos de primer orden</td>
      <td>300 Hz</td>
    </tr>
    <tr>
      <td>Medios</td>
      <td>Pasa altos + pasa bajos en cascada</td>
      <td>500 Hz y 4 000 Hz</td>
    </tr>
    <tr>
      <td>Agudos</td>
      <td>Pasa altos de primer orden</td>
      <td>5 000 Hz</td>
    </tr>
  </table>
</div>

## Configuración de circuitos

Emplea tres pasos en orden:

1. Generar esquemas editables de Qucs-S (.sch) y dibujarlos con matplotlib.
2. Simularlos con el netlister de Qucs-S y Ngspice.
3. Leer los resultados.

Las figuras y la simulación proceden exactamente del mismo circuito.

**Entrada [1]:**

```python
import sys, warnings
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from IPython.display import Image, display

CARPETA = Path("esquemas").resolve()
RECURSOS = Path("recortes")
RECURSOS.mkdir(exist_ok=True)
sys.path.insert(0, str(CARPETA))
import qucs as q

warnings.filterwarnings("ignore", category=UserWarning)
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
TINTA, TINTA_2, REJILLA = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
    "axes.edgecolor": "#b9b8b3", "axes.labelcolor": TINTA_2,
    "xtick.color": TINTA_2, "ytick.color": TINTA_2, "axes.grid": True,
    "grid.color": REJILLA, "grid.linewidth": 0.8, "lines.linewidth": 2,
    "axes.spines.top": False, "axes.spines.right": False,
    "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "legend.frameon": False,
})

def mostrar(fig, nombre, dpi=130):
    ruta = RECURSOS / f"{nombre}.png"
    fig.savefig(ruta, dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    display(Image(filename=str(ruta)), metadata={"archivo": ruta.as_posix()})

def es(x, dec=2):
    texto = f"{x:,.{dec}f}".replace(",", " ").replace(".", ",")
    return texto

rutas = q.generar_todos(CARPETA)
print(f"{'Archivo':<24} {'R graves':>9} {'R medios inf.':>13} {'R medios sup.':>13} {'R agudos':>9}  Sumador (G, M, A)")
for ruta, (nombre, (rc, suma, desc)) in zip(rutas, q.VARIANTES.items()):
    print(f"{ruta.name:<24} {rc['R_B']:>9} {rc['R_M1']:>13} {rc['R_M2']:>13} {rc['R_A']:>9}  {', '.join(suma)}")
```

Se generan seis variantes del mismo circuito:

**Salida [1]:**

```text
Archivo                   R graves R medios inf. R medios sup.  R agudos  Sumador (G, M, A)
01_original.sch                270           150            18        33  10k, 10k, 10k
02_ajustado.sch              530.5        159.15         19.89     31.83  10k, 10k, 10k
03_comercial_E96.sch           536           158            20      31.6  10k, 10k, 10k
04_realce_graves.sch         530.5        159.15         19.89     31.83  5k, 20k, 20k
05_realce_medios.sch         530.5        159.15         19.89     31.83  20k, 5k, 20k
06_realce_agudos.sch         530.5        159.15         19.89     31.83  20k, 20k, 5k
```

### Circuito completo

**Entrada [2]:**

```python
fig = q.dibujar_sch(CARPETA / "02_ajustado.sch", escala=0.95)
mostrar(fig, "c01_ecualizador_completo", dpi=120)
```

**Salida [2]:**

![ecualizador completo](recortes/c01_ecualizador_completo.png)

*Figura 1. Esquema Qucs-S completo con los valores ajustados de los bloques de simulación AC (10 Hz–100 kHz, 401 puntos) y transitoria (10 ms).*

La salida del preamplificador, alimenta un bus común a las tres ramas. Cada red RC excita la entrada no inversora de un amplificador operacional con $R_G=1\,\mathrm{M}\Omega$ y $R_F=100\,\Omega$ ($K\approx1{,}0001$), que la aísla de la carga. Las salidas llegan al nodo de suma del inversor a través de $R_{SB}$, $R_{SM}$ y $R_{SA}$, que son los controles de banda.

### Etapas ampliadas

La misma función recorta el esquema completo por regiones. Las figuras 2 a 6 no son dibujos independientes: salen del mismo archivo `02_ajustado.sch`.

**Entrada [3]:**

```python
etapas = {
    "preamplificador": "Preamplificador no inversor · K = 1 + 500/330",
    "graves": "Graves · pasa bajos RC + buffer",
    "medios": "Medios · pasa altos (500 Hz) y pasa bajos (4 kHz) en cascada",
    "agudos": "Agudos · pasa altos RC + buffer",
    "sumador": "Sumador inversor · controles de banda",
}
for i, (clave, titulo) in enumerate(etapas.items(), start=2):
    fig = q.dibujar_sch(CARPETA / "02_ajustado.sch", vista=q.VISTAS[clave],
                        escala=1.35, titulo=titulo, simulaciones=False)
    mostrar(fig, f"c{i:02d}_{clave}", dpi=110)
```

**Salida [3]:**

![preamplificador](recortes/c02_preamplificador.png)

![graves](recortes/c03_graves.png)

![medios](recortes/c04_medios.png)

![agudos](recortes/c05_agudos.png)

![sumador](recortes/c06_sumador.png)

*Figuras 2 a 6. Preamplificador, rama de graves, rama de medios, rama de agudos y sumador inversor, en ese orden.*

## Modelo analítico

**Preamplificador.** Con realimentación negativa, la ganancia no inversora es $K=1+R_F/R_G=1+500/330\approx2{,}515$.

**Filtros.** Cada red RC tiene su corte en $f_c=\dfrac{1}{2\pi RC}$. Con el buffer de ganancia $K$:

$$H_{PB}(s)=\frac{K}{1+sRC},\qquad H_{PA}(s)=K\,\frac{sRC}{1+sRC},\qquad H_M(s)=H_{PA}(s)\,H_{PB}(s).$$

**Sumador.** Con resistencias de entrada $R_i$ y realimentación $R_F$:

$$V_o=-R_F\left(\frac{V_G}{R_{SB}}+\frac{V_M}{R_{SM}}+\frac{V_A}{R_{SA}}\right).$$

La celda calcula los cortes teóricos de las tres variantes de componentes:

**Entrada [4]:**

```python
LIMITES = [("Graves", "R_B", "C_B", 300), ("Medios inferior", "R_M1", "C_M1", 500),
           ("Medios superior", "R_M2", "C_M2", 4000), ("Agudos", "R_A", "C_A", 5000)]
DISENOS = {"Original": q.ORIGINAL, "Ajustado": q.AJUSTADO, "E96": q.COMERCIAL}

def fc(rc, r, c):
    return 1 / (2 * np.pi * q.valor(rc[r]) * q.valor(rc[c]))

print(f"{'Límite':<16}{'Meta':>8}" + "".join(f"{d:>12}" for d in DISENOS) + "   (Hz, analítico)")
for nombre, r, c, meta in LIMITES:
    print(f"{nombre:<16}{meta:>8}" + "".join(f"{es(fc(rc, r, c)):>12}" for rc in DISENOS.values()))
```

**Salida [4]:**

```text
Límite              Meta    Original    Ajustado         E96   (Hz, analítico)
Graves               300      589,46      300,01      296,93
Medios inferior      500      530,52      500,02      503,65
Medios superior    4.000    4.420,97    4.000,88    3.978,87
Agudos             5.000    4.822,88    5.000,16    5.036,55
```

### Frecuencias de corte simuladas

Cada corte se mide a −3 dB de la ganancia de paso de su etapa: graves y agudos respecto del preamplificador, el límite inferior de medios bajos y el superior con medios altos.

**Entrada [5]:**

```python
def cortes(a):
    f = a["frequency"]
    return [q.corte(f, a["graves"] / a["pre"], sube=False),
            q.corte(f, a["medio_alto"] / a["pre"], sube=True),
            q.corte(f, a["medios"] / a["medio_alto"], sube=False),
            q.corte(f, a["agudos"] / a["pre"], sube=True)]

tabla = {"Original": cortes(sim["01_original"]["ac"]),
         "Ajustado": cortes(sim["02_ajustado"]["ac"]),
         "E96": cortes(sim["03_comercial_E96"]["ac"])}
print(f"{'Límite':<16}{'Meta':>8}" + "".join(f"{d:>12}" for d in tabla) + "   error E96")
for i, (nombre, _, _, meta) in enumerate(LIMITES):
    err = 100 * (tabla["E96"][i] / meta - 1)
    print(f"{nombre:<16}{meta:>8}" + "".join(f"{es(v[i]):>12}" for v in tabla.values())
          + f"   {err:+.1f} %".replace(".", ","))
```

**Salida [5]:**

```text
Límite              Meta    Original    Ajustado         E96   error E96
Graves               300      589,63      300,34      297,26   -0,9 %
Medios inferior      500      530,52      500,01      503,65   +0,7 %
Medios superior     4000    4 420,85    4 000,81    3 978,89   -0,5 %
Agudos              5000    4 811,81    4 987,81    5 023,88   +0,5 %
```

Los valores ajustados alcanzan las metas con un error inferior al 0,3 %. Con resistencias E96 el error máximo es del 1 %, del mismo orden que la tolerancia de esos componentes.
