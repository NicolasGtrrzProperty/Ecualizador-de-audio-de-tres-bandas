# Ecualizador de audio de tres bandas

Repositorio para ilustrar un ecualizador de tres bandas (Grave, medio y agudo) para una señal de audio, mediante circuitos activos RC y amplificadores operacionales.

Los circuitos electrónicos se generan con esquemas de **Qucs-S**, se simulan con **Ngspice**, se dibujan con **Python** y se modelan con **Manim**.

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

## Propósito
