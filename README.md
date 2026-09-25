# Ecualizador de audio de tres bandas

Repositorio para ilustrar un ecualizador de tres bandas (Grave, medio y agudo) para una señal de audio, mediante circuitos activos RC y amplificadores operacionales.

Los circuitos electrónicos se generan con esquemas de **Qucs-S**, se simulan con **Ngspice**, se dibujan con **Python** y se modelan con **Manim**.

## Resumen

Se diseño un ecualizador activo que comprende señales con frecuencias de **300 Hz** (límite superior de graves), **500 - 4.000 Hz** (medios) y **5.000 Hz** (límite inferior de agudos).

        | Banda | Tipo de filtro | Frecuencias objetivo (−3 dB) |
        |---|---|---: |
        | Graves | Pasa bajos de primer orden | 300 Hz |
        | Medios | Pasa altos + pasa bajos en cascada | 500 Hz y 4 000 Hz |
        | Agudos | Pasa altos de primer orden | 5 000 Hz |

## Propósito
