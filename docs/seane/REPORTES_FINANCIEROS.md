# SEANE — Inventario de reportes del módulo financiero (préstamos)

> Fuente: sistema Visual FoxPro en `SEANE/sis-sql/` (solo lectura). La app Django `SEANE/SEANE/` quedó fuera del alcance por instrucción expresa.
> Todas las rutas son relativas a `SEANE/sis-sql/`. "L" = número de línea. Las etiquetas entre comillas son textuales de SEANE.
> Fecha del levantamiento: 2026-10-21.

## 0. Cómo se levantó el inventario

- **Menús.** El menú del módulo no está en un `.MNX`: es el formulario `ventas/menupre.SCX` ("Sistema de Préstamos", botones 1–9, A, B y C), más tres popups en código: `ventas/PRE_MENUREP.PRG` (reportes, L3-L15), `ventas/pre_menuacc.PRG` (accesorios, L3-L10) y `ventas/pre_menuinv.prg` (inversiones, L3-L15).
- **FRX/SCX.** Los decodifiqué como tablas DBF con un parser propio: lee el `.FRX`/`.SCX` y su memo `.FRT`/`.SCT`, y saca `EXPR`, `PICTURE`, `TOTALTYPE`, `SUPEXPR` (condición "print when") y los `Caption`/`ControlSource` de los formularios de filtros.
- **Reportes en texto.** La mayoría NO usa FRX. Son programas `.PRG` que imprimen con `?`/`??` a un archivo `.rep` (`set alternate to`) y luego lo muestran en pantalla (`despleg`) o lo mandan a la impresora (`impr_rep`). Las columnas salen del `encabezado` de cada PRG y de las líneas `??` del detalle.
- **xfrxlib.** En el módulo de préstamos no se usa. Ningún PRG `pre_*` lo invoca; la salida es `REPORT FORM ... PREVIEW/TO PRINT` o texto plano. Solo se exportan algunos cursores a Excel con `export to ... type xl5`.
- **Barrido.** Revisé los 181 `.FRX` buscando los que tocan datos de préstamo, pago, inversión, caja, mora o cheque. Los que pertenecen a otros módulos se listan en el Anexo A.

**Total: 51 entradas numeradas** (38 reportes y documentos propios del módulo, contando cada formato; 6 documentos de recibos y notas; 3 reportes relacionados de otros módulos; 1 opción sin implementar y 1 stub).

Leyenda: **TXT** = PRG que imprime texto. **FRX** = Report Form de VFP. **RTF** = plantilla Word con reemplazo de marcadores. **XLS** = exportación Excel 5.

---

## A. Menú "8.-Reportes" del Sistema de Préstamos (`ventas/PRE_MENUREP.PRG`)

Permiso: cada opción exige su letra en `unos_i.prestamo_rep` o, si falta, la clave de un supervisor (`do pide_clave`) (PRE_MENUREP.PRG L35-L44 y siguientes).

### 1. "1.- Balance de Cuotas"
- **Fuente:** `ventas/pre_repbalcu.PRG` (TXT) y `ventas/pre_repbalcu.SCX` ("Balance de Cuotas"). Desde el menú se llama con `WITH 0` (PRE_MENUREP L45); el recibo de ingreso lo llama en modo automático con `WITH 1` (pre_pago.SCX, Text6.Valid).
- **Propósito:** tabla de amortización viva de un préstamo con el saldo pendiente de cada cuota a una fecha de corte.
- **Filtros:** "Deudor" (cliente y luego el préstamo con `selec_pre`), "Calcular Intereses Hasta", "Formato(1,2)", "Imprimir", "Imprimir intimación".
- **Orden:** el de las cuotas (`cuota` por `fec, s`, varios.PRG L2538).
- **Encabezado** (L152-L224): "Préstamo No.", "Deudor" + "Cedula", "Dirección", "Teléfono", "Fiador"/"Tel. Fiador", "Acreedor", "Monto Préstamo" (`mon+adi`), "Int/Acr." (`int`% + `fpa`), "Comisión", "Mora", "Fecha Préstamo", "Tiempo" (`ncu` + Días/InterDías/Semanas/Quincenas/Mes(es)), "Balance/Capital", "Balance Real", "Balance/Cuotas", "Int.Tot." (`int+com`).
- **Columnas** (L42, L82-L111):
  - "CUOTA#": `j/mcant_paga`; una ND sale como `ND`, un incremento de capital como `PREST`, el solo interés como `j/?`; "A" marca las adicionales.
  - "FECHA" → `arfec`; "MONTO-CUOTA" → `arcuotas` (monto original).
  - "CAPITAL", "INTERES", "MORA", "OTROS", "MORA-OTROS" → `arcap`, `arint`, `armor`, `arcom`, `armoc`, como saldo pendiente.
  - "SALDO/CUOTA" → suma de los cinco.
- **Totales** (L112-L119): suma de cada componente y total. Al imprimir agrega "Balance del Capital", "Balance real" y "Balance/cuotas".
- **Cálculo** (`est_pre`, varios.PRG L2694-L2771, que capitaliza la mora con `capit_cuo` L2611-L2682):
  - "Balance real" = capital total + todo lo vencido + interés y comisión de la cuota en curso prorrateados por días (L2732-L2749).
  - "Balance/Cuotas" = suma de los saldos de todas las cuotas, incluyendo intereses futuros (L2758).
- **Notas:** el formato 2 no hace nada (`repbalc2` comentado y `return`, L52-L55). "Imprimir intimación" encadena el documento 41 (L139-L141).

### 2. "2.- Estado de Cuenta de Préstamo"
- **Fuente:** `ventas/pre_estpre.prg` (TXT) y `ventas/PRE_estpre.SCX`.
- **Propósito:** historial de cargos y pagos de un préstamo con el balance resultante.
- **Filtros:** "Deudor", "Calcular Intereses Hasta", "Simple/Detallado (S/D)", "Imprimir".
- **Orden:** pagos por `s` excluyendo anulados `est='C'` (L82-L84). En el detallado se intercalan las cuotas por fecha (L182-L199).
- **Formato Simple** ("FECHA/PAGO  INT. HASTA     PRESTAMO    INT./MORA         PAGO      BALANCE", L299): primera línea con fecha, monto y balance inicial `mon+adi`; si el balance cambió entre pagos, una línea "INT./MORA" con lo devengado (`pago.bal + monto − balance anterior`, L145-L155); luego el pago (`fep`, `fec`, monto o `ND`, `pago.bal`); al final, lo devengado hasta el corte (L171-L178).
- **Formato Detallado** ("FECHA/PAGO  INT. HASTA   OPERACION        CARGOS         PAGOS       CAPITAL       INTERES      COMISION          MORA       BAL/CUO     BAL/PREST", L301): líneas "Cuot #n"/"Debito" con el cargo y el saldo por componente (L202-L220); líneas "Pago"/"Crédito" con monto, distribución `cap/int/com/mor+moc` y `bal` (L223-L247). Las ND no se imprimen como pago (L224-L226).
- **Totales:** "Balance del Capital", "Balance real", "Balance/cuotas" (L96-L101).
- **Cálculo:** el interés devengado entre pagos se deduce por diferencia de balances, no se recalcula.

### 3. "3.- Reporte de Préstamos": Formato 1 (general)
- **Fuente:** `ventas/pre_reppre.PRG` (motor común) + `ventas/pre_reppre1.PRG`. Formulario `ventas/pre_reppre.SCX`.
- **Propósito:** listado de cartera por préstamo con montos, pagado, mora, cuotas y balances.
- **Filtros (comunes a los formatos 1-6):**
  - Estado: "Incluir Préstamos Saldados (S/N)", "Incluir Préstamos No Saldados (S/N)", "Sólo Préstamos Atrasados (S/N)", "Sólo Préstamos Vencidos(S/N)", "Cuotas Atrasadas >= ?".
  - Fechas: "Fecha Inicial"/"Fecha Final" (fecha del préstamo), "Calcular Intereses Hasta", "Recalcular Préstamos Hasta", "Préstamos Saldados  Desde"/"Hasta".
  - Clasificación: "Tipo de Préstamos", "Clase", "Garantía (Prendaria/Hipotecaria/Solidaria/Otra)", "Frecuencia de pago (Diario/InterD/Semanal/Quinc/Mensual)".
  - Personas: "Acreedor", "Fiador", "Deudor".
  - Presentación: "Ordenado por Préstamo/Deudor (P/D)", "Tipo de Balance (Real/Cuotas)", "Formato (1,2,3,4/5/6) ?", "Imprimir".
- **Orden:** `cli,fec,s` o `cod` (L131-L135).
- **Columnas** (pre_reppre1 L4, L15-L29): "DEUDOR", "PRESTAMO #", "TIPO", "GAR" (`tga`), "FECHA", "MONTO PREST" (`mon+adi`), "TOTAL PAGADO" (`pac`), "MORA-ACU" (`mbalmor`), "CUOT" (`mcant_paga`), "MONTO CUOTA", "CUOT FALT", "CUOT ATR.", "BAL.CAP.", "BAL. GRAL" (`mbalreal` o `mbalpre`).
- **Totales** (L39-L49): préstamos, monto, pagado, mora, cuota, balance de capital y balance general.
- **Cálculo:** condiciones de inclusión en pre_reppre.PRG L301-L305. "Recalcular hasta" reconstruye el préstamo con los pagos hasta esa fecha (`pre_recalpre WITH 1`, L165).
- **Exportación:** el cursor `reporte` (con los buckets de antigüedad) siempre se exporta a `exportar\reporte_prestamos` XL5 (L344-L351).

### 4. "3.- Reporte de Préstamos": Formato 2 (resumido)
- **Fuente:** `ventas/pre_reppre2.PRG`.
- **Columnas** (L11): "DEUDOR", "PRESTAMO #", "FECHA", "MONTO PREST", "MORA-ACU", "CANT CUOTAS", "CUOT ATR.", "BAL.CAP.", "BAL. GRAL".
- **Totales:** préstamos, monto, mora, balance de capital y general (L40-L47).

### 5. "3.- Reporte de Préstamos": Formato 3 (interés mensual)
- **Fuente:** `ventas/pre_reppre3.PRG`.
- **Columnas** (L11): "DEUDOR", "PRESTAMO #", "FECHA", "MONTO PREST", "CUOTAS", "MONTO-CUOTA", "BAL.CAP.", "INT/MENSUAL".
- **Cálculo** (L23-L31): solo interés → `balcap*int/100`; los demás → `cuo − mon/cant_paga` (la parte de interés de una cuota flat).
- **Totales:** monto, balance de capital y suma del interés mensual (L54-L60).

### 6. "3.- Reporte de Préstamos": Formato 4 (DataCrédito)
- **Fuente:** `ventas/pre_reppre4.PRG`. Genera `exportar\DATACREDITO` XL5 (L102-L110).
- **Columnas** (L141-L146, cursor L9-L17): "CODIGO", "NOMBRE", "CEDULA" (o RNC), "DIRECCION", "TELEFONO", "PRESTAMO#", "FECHA-PRESTAMO", "FECHA-VENCIMIENTO" (`arfec(mcancuo)`), "MONTO-PRESTAMO", "CANTIDAD-DE-CUOTAS", "MONTO-DE-CUOTA", "CUOTAS-ATRASADAS", " MONTO-VENCIDO", "FECHA-ULTIMO-PAGO", "MONTO-ULTIMO-PAGO", "BALANCE-AL-CORTE", "FORMA-DE-PAGO" ('C = CUOTAS'), "CODIGO-DE-MONEDA" ('DO'), "DESCRIPCION-MONEDA" ('RD$ PESOS REPUBLICA DOMINICANA'), "STATUS".
- **STATUS** (L31-L42): `balcap<1` 'SALDADO'; `dias_atraso>=240` 'CASTIGADO'; `>=120` 'LEGAL'; `>=60` 'MORA'; si no 'NORMAL'. `dias_atraso = date() − primera cuota con capital > 1` (pre_reppre L176-L188): se mide contra la fecha del sistema, no contra el corte.
- **Nota:** fuerza el balance real (pre_reppre L58-L60).

### 7. "3.- Reporte de Préstamos": Formato 5 (CICLA/TransUnion)
- **Fuente:** `ventas/pre_reppre5.PRG`. Archivo de ancho fijo.
- **Posiciones** (`at`, L21-L46): 'I', nombre@1, cédula/RNC sin guiones@117, teléfono@274, dirección@288, préstamo@488, fecha AAAAMMDD@629, monto@639, cuotas@659, cuota redondeada@662, último pago@672, balance@682, vencido@692, buckets `m_30…m_210`@702-762.
- **Encabezado** (L79-L91): trae columnas del layout CICLA que no se llenan ("CED.VIE", "NACIONALIDAD", "NOMBRE-DEL-CONYUGE", "LIM.-CRE.", …). Los buckets se rotulan "1-29DIAS", "30-59DIAS", "60-89DIAS", "90-119D", "120-149D", "150-179D", "180D-MAS".
- **Nota:** esos rangos no coinciden con el cálculo real (0-30, 31-60, …), y 31-60 y 61-90 siempre salen en cero (ver 8).

### 8. "3.- Reporte de Préstamos": Formato 6 (Antigüedad de saldos)
- **Fuente:** `ventas/pre_reppre6.PRG`.
- **Columnas** (L10): "DEUDOR", "PRESTAMO #", "FECHA", "MONTO PREST", "0-30 DIAS", "31-60 DIAS", "61-90 DIAS", "91-120 DIAS", "&gt;120 DIAS".
- **Cálculo** (pre_reppre.PRG L268-L298): cada cuota vencida suma su saldo total al bucket según `mfec_final − arfec(i)`. Hay siete cortes (&gt;180, &gt;150, &gt;120, &gt;90, &gt;60, &gt;30, resto); el reporte junta los tres últimos en "&gt;120".
- **Totales:** suma por bucket y conteo (L41-L48).
- **Errores:** (a) pre_reppre.PRG L317 hace `m_60 WITH m_60, m_90 WITH m_90` en vez de `m60`/`m90`, así que 31-60 y 61-90 quedan siempre en 0 en el cursor, el Excel y los formatos 5 y 6. (b) El detalle de pre_reppre6 (L26-L30) imprime las variables de memoria `m30…m210` (las del último préstamo calculado) y no los campos `m_30…m_210`: todas las filas muestran lo mismo. Los totales (L31-L37) sí usan los campos.

### 9. "4.- Reporte de Cuentas por Cobrar"
- **Fuente:** `ventas/PRE_repcxc.PRG` (TXT) y `ventas/pre_repcxc.SCX`.
- **Filtros:** "Tipo de Préstamos", "Clase de Préstamos", "Garantía", "Frecuencia de pago", "Ordenado por Préstamo/Deudor (P/D)", "Formato (1/2) ", "Imprimir". El corte siempre es `date()` y no se puede elegir (L10).
- **Orden:** `cli,fec,s` o `cod` (L45-L49).
- **Columnas F1** (L286): "PRESTAMO #", "DEUDOR", "FECHA", "CAPITAL", "INTERES", "MORA" (`mor+moc`), "COMISION", "BALANCE".
- **Columnas F2** (L317): "PRESTAMO #", "DEUDOR", "FECHA", "CAPITAL", "INTERES" (`int+com`), "MORA", "BALANCE".
- **Totales:** préstamos y suma por columna (L170-L187).
- **Cálculo:** `int` suma el interés de todas las cuotas pendientes, incluso el que no ha vencido (`mbalint`, varios.PRG L2713). La cuenta por cobrar incluye interés no devengado.

### 10. "5.- Reporte de Cobros": Formato 1 (detallado)
- **Fuente:** `ventas/PRE_REPCOB.PRG` (TXT) y `ventas/pre_repcob.SCX`.
- **Propósito:** qué cuotas vencidas o por vencer se deben cobrar a cada deudor en un rango de fechas.
- **Filtros:** "Calcular Intereses Hasta", "Fecha Inicial"/"Fecha Final" (vencimiento), "Ordenado por Deudor/Préstamo/Fecha (D/P/F)", "Sólo Nombre del  Deudor (S/N)", "Formato(1/2/3/4)", "Tipo de Préstamos", "Clase", "Garantía", "Frecuencia de pago", "Cuotas Atrasadas Mayores o Igual que", "Días de Vencimiento de Cuotas Mayores o Igual que", "Préstamo Inicial"/"Préstamo Final", "Deudor", "Excluir clientes con llamadas pendientes", "Imprimir".
- **Orden:** deudor o préstamo; con F se arma un cursor `repcobfe` indexado por fecha (L111-L113).
- **Bloque por préstamo** (L297-L355): nombre, "Direcc", "Tel.", fiador con teléfono y dirección, "Acreedor" (modo administración), "Prést#; Monto= … de Fecha", "Fecha 1ra Cuota", "Fecha Ultima Cuota", "Fecha del Ultimo Pago; Ult. Pago", "Bal Cap; Bal. Real; Bal.Cuotas".
- **Columnas** (L108): "CUOTA #" (n/total, ND, `?` o sufijo `A`), "FECHA", "MONTO-CUOTA", "MORA" (`mor+moc`), "SALDO".
- **Totales:** subtotal por préstamo (L420-L423); total de préstamos, mora y vencido (L186-L190).
- **Cálculo:** excluye préstamos sin balance o sin nada vencido (`mmonven<0.02`, L265). "Llamada pendiente" = registro en `llamada` con `fec2 > hoy` (L432-L450).
- **Nota:** el total imprime `msummor` antes que `msumcuo` y el encabezado pone MONTO-CUOTA antes que MORA: columnas desalineadas.

### 11. "5.- Reporte de Cobros": Formato 2 (resumido por fecha)
- **Fuente:** `ventas/pre_repcob2.PRG`.
- **Columnas** (L12): "DEUDOR", "TELEFONO", "PRESTAMO#", "FECHA", "CUOTA", "MORA", "SALDO".
- **Orden:** fecha de vencimiento, cliente y préstamo (L83-L84).
- **Totales:** cuotas, mora y saldo (L99-L103).

### 12. "5.- Reporte de Cobros": Formatos 3 y 4 (ticket por cliente)
- **Fuente:** `ventas/pre_repcob3.PRG`. F3 = Epson con ESC (L220-L292); F4 = cinta Star (L295-L376). Imprime directo a LPT/`mpuerec` (L102-L106). Comentario L2: "como lo usan en INTERSA".
- **Propósito:** volante que el cobrador entrega al cliente.
- **Campos:** compañía; "Fecha"; "Cobrador:" (usa `prestamo2.tip`, el tipo de préstamo, como código de cobrador); "Cliente", "Direcc.", "Tel."; "Préstamo No."; "Total Prestado" (`ncu*cuo`); "Plan de pago"; "Total de Pagos"; "Cuotas Pagadas"; "Monto Cuota"; "Abonos"; "Cuotas Vencidas"; "Monto Vencido"; "Mora por atraso"; "TOTAL A PAGAR"; "ABONO:____"; "Entregado Por"/"Recibido Por"; "Balance Pagado"; "Balance Pendiente".
- **Cálculos:** "Monto Vencido" = `mmonven − mbalmor + (cuo − saldo de la cuota siguiente)` (L269). "Total Prestado" es en realidad el total a pagar.
- **Totales:** préstamos, "Total de mora", "Total vencido" (L86-L92).

### 13. "6.- Reporte de Atrasos"
- **Fuente:** `ventas/pre_repatr.PRG` (TXT) y `ventas/pre_repatr.SCX`.
- **Filtros:** "Calcular Intereses Hasta", "Garantía", "Ordenado por (Préstamo/Deudor)", "Tipo de Préstamos", "Clase", "Frecuencia de Pago", "Formato (1..2)", "Excluir clientes con llamadas pendientes", "Imprimir".
- **Columnas F1** (L41): "DEUDOR", "TELEFONO", "PRESTAMO #", "FECHA", "MONTO" (`mon+adi`), "CUOT", "MONTO/CUOTA", "CUO-ATR", "MORA" (`mbalmor`, sin `moc`), "ATRASO" (`mmonven`).
- **Columnas F2** (L39): "DEUDOR", "TELEFONO", "FECHA", "MONTO-PREST", "MONTO-CUOTA", "CUO-ATR", "MORA", "ATRASO".
- **Totales:** préstamos, monto, mora y atraso (L170-L186).
- **Nota:** el encabezado del F2 rotula la clase como "Tipo de Préstamos" (L329-L330).

### 14. "7.- Reporte de Ingresos": Formato 1
- **Fuente:** `ventas/pre_reping.PRG` (motor) + `ventas/pre_reping1.PRG`. Formulario `ventas/pre_reping.SCX`.
- **Propósito:** recibos, NC y ND de un período con la distribución del dinero.
- **Filtros (formatos 1-5):** "Fecha Inicial"/"Fecha Final" (sobre `fep`), "Recibo Inicial"/"Recibo Final", "Tipo de Préstamos", "Clase", "Garantía", "Frecuencia de pago", "Préstamo#", "Acreedor", "Fiador", "Deudor", "Incluir  Pagos (S/N)", "Incluir Notas de Crédito (S/N) ", "Incluir Notas de Débito (S/N)", "Incluir Recibos Cancelados", "Incluir Recibos NO Cancelados", "Incluir Conceptos", "Formato (1,2,3,4,5)", "Imprimir".
- **Orden:** `fep,s` (L144).
- **Columnas** (pre_reping1 L155): "CODIGO", "DEUDOR", "PRESTAMO #", "RECIBO#", "FECHA" (`fep`), "INT.HASTA" (`fec`), "PAGO" (solo `tip='P'`), "NOTA-CRED" (con sufijo NC/ND), "ABONO CAP", "INTERES", "MORA", "OTROS" (`com+moc`), y opcionalmente "Concepto:".
- **Totales:** pagos, NC+ND, capital, interés, mora, otros y conteos (L37-L51).
- **Exportación:** `exportar\reporte_ingresos_prestamos` XL5 (pre_reping L151-L157).
- **Error:** el filtro (pre_reping1 L30-L31) solo excluye P/C/D. Los registros de cambio de tasa (`tip='T'`/`'M'`, con `mon` = tasa y `cod=0`) se cuelan: en F2 salen bajo "PAGO" y en F5 se suman al total de PAGO (pre_reping5 L26-L27).

### 15. "7.- Reporte de Ingresos": Formato 2
- **Fuente:** `ventas/pre_reping2.PRG`.
- **Columnas** (L3): "DEUDOR", "PRESTAMO #", "RECIBO#" (NC/ND con prefijo y `cod%10000000`), "FECHA", "PAGO", "ABONO CAP", "INTERES", "MORA", "OTROS".
- **Totales:** "PAGO" = pagos + créditos (L41); conteos.

### 16. "7.- Reporte de Ingresos": Formato 3 (neto de comisiones)
- **Fuente:** `ventas/pre_reping3.PRG`.
- **Columnas** (L3): "DEUDOR", "PRESTAMO #", "RECIBO#", "FECHA", "INT.HASTA", "PAGO", "NOTA-CRED", "ABONO CAP", "INTERES", "MORA".
- **Cálculo:** PAGO y NOTA-CRED sin comisión (`mon−com−moc`, L80-L89); el total también la resta (L41). Muestra lo que corresponde al acreedor.

### 17. "7.- Reporte de Ingresos": Formato 4 (hora y usuario)
- **Fuente:** `ventas/pre_reping4.PRG`.
- **Columnas** (L3): "DEUDOR", "PRESTAMO #", "RECIBO#", "FECHA", "INT.HASTA", "PAGO", "HORA", "USUARIO".
- **Totales:** pagos (L39-L46). Sirve para auditar quién cobró.

### 18. "7.- Reporte de Ingresos": Formato 5 (resumen por cliente)
- **Fuente:** `ventas/pre_reping5.prg`.
- **Columnas** (L4): "DEUDOR", "PAGO", "NC", "ND", "ABONO CAP", "INTERES", "MORA", "OTROS". Agrupado por `cli` (L6-L34).
- **Totales:** por columna (L84-L92).

### 19. "8.- Reporte de Proyección de Ganancias"
- **Fuente:** `ventas/pre_repproga.PRG` (TXT) y `ventas/pre_repproga.SCX`.
- **Filtros:** "Fecha Inicial"/"Fecha Final", "Tipo de Préstamos", "Clase de préstamos", "Garantía", "Frecuencia de pago", "Ordenado por Deudor/Préstamo/Fecha (D/P)", "Imprimir".
- **Columnas** (L49): "DEUDOR", "PRESTAMO #", "TIP", "GAR", "FECHA", "MONTO PREST" (`mon+adi`), "CUOT", "MONTO CUOTA", "TOTAL" (`ncu*cuo` + las cuotas adicionales), "GANANCIA" (`TOTAL − (mon+adi)`).
- **Totales:** préstamos, monto, total y ganancia (L165-L172).
- **Cálculo:** usa el plan original. No considera pagos, mora real, NC ni cambios de tasa, y cuenta como ganancia la comisión que en modo administración es de la oficina.

### 20. "9.- Reporte de Gastos de Préstamos"
- **Fuente:** `ventas/pre_repgas.PRG` (TXT) y `ventas/pre_repgas.SCX`.
- **Filtros:** los de 19 más "Formato (1,2)".
- **Columnas F1** (L51): "PRESTAMO#", "CLIENTE", "FECHA", "MONTO PREST", "GAS. CIERRE" (`gac`), "GAS. LEGALES" (`gal`), "HONORARIOS" (`hon`), "OTROS GASTOS" (`oga`), "TOTAL GASTOS".
- **Columnas F2** (L49): "PRESTAMO#", "CLIENTE", "FECHA", "MONTO PREST", "GAS. CIERRE" (aquí muestra `oga`, el campo que la pantalla llama "Cierre"/"Otros Gastos").
- **Totales:** por columna (L166-L181).

### 21. "A.- Imprimir Pagareses": pagaré en Word (RTF)
- **Fuente:** `ventas/pre_imp_paga.PRG` L9-L12 → `ventas/pre_imp_paga_word.PRG`. Plantillas `config\pagare.rtf` o `config\pagare_garante.rtf` (si hay fiador). También se dispara al grabar un préstamo nuevo (pre_prestamo.SCX Command1.Valid).
- **Marcadores** (L148-L165): NOMBRE_CLIENTE (deudor "Y" fiador), CEDULA_CLIENTE, DIRECCION_CLIENTE, CLIENTE_1, FIADOR_1, VALOR_INMUEBLE_LETRA/NUMERO (`val_gar` en USD), VALOR_INICIAL_LETRA/NUMERO (`mon+adi` en USD), MONTO_SEPARACION_*, DESCRIPCION_INMUEBLE (memo `gar`), FECHA_ENTREGA, TABLA_CUOTAS, MONTO_FINANCIADO_*, FECHA_LETRA.
- **Nota:** hecho para un cliente inmobiliario en dólares (L92-L100, L138-L139). Lee las cuotas de `prestamo` y no de `prestamo2` (L125). `ventas/pre_llena_pagare.PRG` (L1-L78) es una variante con marcadores en minúscula que nadie llama.

### 22. "A.- Imprimir Pagareses": pagaré 8A (Ochoa Hermanos)
- **Fuente:** `ventas/pre_paga_8a.PRG` (si existe `config\ochohnos`), `.SCX` y `.FRX`.
- **Contenido:** "PAGARE No." n/total, "Vence el", texto de venta condicional con "OCHOA HERMANOS, C X A" y "RNC No. 102-00238-1" fijos en el reporte, tabla del vehículo ("TIPO Y MARCA", "MODELO", "COLOR", "CHASIS NO.", "AÑO", "N/U"), "RD$", "NOMBRE", "CEDULA", "DIRECCION", "CIUDAD", "TEL.", "Firmado en Santiago, R. D., hoy", "FIRMA". Dos pagarés por página.
- **Filtros:** "Cliente", "Chasis#1..3", "Ciudad", "Pagaré Inicial"/"Pagaré Final".
- **Cálculo:** valida que el vehículo se le haya vendido al cliente (`vendido_cli`, L130-L147).

### 23. "A.- Imprimir Pagareses": pagaré unificado
- **Fuente:** `ventas/pre_imp_paga.PRG` L73-L99 (si existe `config\pagare.uni`), `ventas/pre_paga_uni.SCX/.FRX`.
- **Contenido:** compañía, dirección, "RNC."; "PRESTAMO NO."; "PAGARE No."; "Vence el"; "Debo y pagaré a … la suma de"; monto en letras; "Valor Recibido en" + objeto; cláusulas ("A mi entera satisfacción…", renuncia de domicilio); espacio "BUENO Y VALIDO"; "POR RD$"; "FIRMADO EN FECHA"; "NOMBRE", "DIRECCION", "CEDULA"; "FIRMA". Dos por página.
- **Filtros:** "Cliente", "Objeto", "Pagaré Inicial"/"Pagaré Final".

### 24. "A.- Imprimir Pagareses": pagaré múltiple preimpreso
- **Fuente:** `ventas/pre_imp_paga.PRG` L100-L113, `ventas/pre_paga_mul.SCX/.FRX`.
- **Contenido:** solo campos (el texto venía en el papel): n/total, `prestamo.cod`, `cuota.fec`, monto en letras y números, nombre, cédula, dirección, ciudad, "Marca", "Modelo", "Chasis", "Año", "Registro", "Placa", "Color", "Motor#". Pide confirmación antes de cada pagaré.
- **Error:** la serie de la cédula se calcula después de recortarla (L45-L50).

### 25. "B- Carta de Cobros"
- **Fuente:** `ventas/pre_car_cob.PRG`, `.SCX` ("CARTA DE COBROS") y `.FRX`.
- **Filtros:** "Fecha de la Carta:", "Fecha de la Cita", "Cuotas Atrasadas" (mínimo), "Cliente".
- **Contenido:** fecha, "Señor(a)", nombre, dirección, "Distinguido señor(a):", "Nos dirigimos a usted para expresarle lo siguiente:", "favor de pasar por nuestra oficina", "antes del día" + cita, "Para tratar asuntos de sumo interés referente a su cuenta", "y de lo contrario nos veremos obligados a que su caso pase al departamento legal.", "Atentamente,", compañía, "GERENTE DE COBROS".
- **Errores:** con cliente indicado imprime una sola carta sin calcular atraso (L61-L66). Sin cliente imprime una por préstamo con `mcuoatr >= mínimo` (L56); con mínimo 0 salen cartas hasta para préstamos saldados.

### 26. "C- Estadísticas de Préstamos": no implementado
- PRE_MENUREP.PRG L199-L211: `do pre_estadis` está comentado y el programa no existe.

### 27. "D- Reporte de Llamadas de Cobros"
- **Fuente:** `ventas/PRE_REP_LLAM.PRG`, `.SCX` y `.FRX`.
- **Filtros:** "LLAMADA ANTERIOR:" Fecha Inicial/Final (`fec1`); "VOLVER A LLAMAR:" Fecha Inicial/Final (`fec2`).
- **Orden:** `fec2,s` (L29).
- **Columnas:** "LLAMADA ANTERIOR", "VOLVER A LLAMAR", "OBSERVACION" (nombre + `OBS`, solo si hay observación).
- **Totales:** conteo de "LLAMADAS".
- **Nota:** `llamada` no guarda préstamo, usuario ni resultado (instalar/bd_pre.sql L251-L255).

---

## B. Documentos emitidos desde las operaciones del préstamo

### 28. Plan de pago: Formato 1
- **Fuente:** `ventas/pre_plan.PRG` (TXT) y `ventas/pre_plan.SCX` ("Cantidad de Copias", "Formato (1/2)", "Imprimir"). Botón "Plan"; se imprime solo al crear un préstamo en modo administración.
- **Encabezado** (L108-L172): "Capital Fijo/Variable; Interés Fijo/Amotizado [sic]; Comisión Fija/Amortizada", "Préstamo#", "Deudor", "Fiador", "Cédula", "Dirección", "Teléfono", "Tel. Fiador", "Acreedor", "Capital", "Interés Acreedor", "Comisión", "Interés Total", "Duración Préstamo", "Vence los días: dd de cada mes", "Fecha Inicial".
- **Columnas** (L169-L170): "Pago #", "Fecha", "Balance anterior", "Abono Capital", "Interés", "Total" (cap+int), "Interés Acreedor" (etiqueta corrida: el valor es `arcom`), "Comisión"/"Total" (`int+com`), "Monto Cuota", "Balance Después", "Firma".
- **Totales:** capital, interés, cap+int, comisión, int+com y "Total a Inscribir" (L74-L83).

### 29. Plan de pago: Formato 2 (resumido)
- **Fuente:** `ventas/pre_PLAN2.PRG`.
- **Encabezado:** condición; datos del deudor salvo que exista `C:\terminal\cot-pre` (modo cotización, L98); "Capital", "tiempo", "Interés", "Mora".
- **Columnas** (L133): "Pago #", "Fecha", "Monto Cuota" (cap+int), "Capital", "Interés", "Balance". Omite la comisión.
- **Totales:** capital e interés (L44-L47).

### 30. Comprobante de préstamo (certificación notarial)
- **Fuente:** `ventas/pre_cerprest.PRG/.SCX`. Solo en modo administración, al crear el préstamo.
- **Contenido** (L36-L99): membrete "BUFETE JURIDICO / LIC. BENITO A. GRULLON R. / ABOGADO NOTARIO" fijo en el código; "COMPROBANTE DE PRESTAMO"; texto "…negocio de hipoteca consentido por {acreedor}, a favor de {deudor}, por la suma de RD$ … por el término de N mes(es)…, pagando cuotas mensuales de capital e interés | pagando interés solamente."; lugar y fecha.
- **Nota:** documento de un solo cliente; no portar tal cual.

### 31. Recibo de Ingreso (FRX estándar)
- **Fuente:** `ventas/pre_impr_rec.PRG` (despachador, L40-L129) + `ventas/pre_impr_rec.FRX`.
- **Campos:** compañía, dirección, "R.N.C.", "Tel."; tipo de NCF (`TIP_NCF()`, L147-L169) y "NCF#:"; "RECIBO DE INGRESO"; "FECHA:" `fep`; "PRESTAMO NO.:"; "RECIBO No.:"; "HEMOS RECIBIDO DE:"; "RNC/CEDULA:"; "LA SUMA DE:" en letras (en dólares si `config.co3` dice 'DOLAR', L18-L21) y números; "POR CONCEPTO DE:"; "TOTAL ="; "CAJERO"; `confpre.com_rec`.

### 32. Recibo con distribución por pagaré (FRX re2)
- **Fuente:** `ventas/pre_impr_re2.FRX` (si existe `config\OCHOHNOS`, pre_impr_rec L56-L90); datos capturados en `ventas/pre_pago3.SCX`.
- **Campos extra:** "FORMA DE PAGO:" (texto libre), "DISTRIBUCION DEL PAGO" con hasta 4 "PAGARE# n" y su monto (`c1..c4`/`cm1..cm4`), "OTRAS CUOTAS", "MORA", "TOTAL".
- **Errores:** las condiciones usan `pago.c1` en vez de `pago2.c1`; pre_pago3.SCX calcula la mora con `pago.c_otr`/`pago.mora`, que no existen.

### 33. Recibo con distribución y balance (FRX re4)
- **Fuente:** `ventas/pre_impr_re4.FRX` (`confpre.for_rec=4`).
- **Campos extra:** "CODIGO:"; nombre "Y/O" fiador; "PROJECTO:" (`tip`) y "CLASE:"; "ABONO A CAPITAL", "INTERES" (`int+com`), "MORA" (`mor+moc`); "CUOTAS SALDADAS    ="; "BALANCE TOTAL      ="; "FECHA DEL PROXIMO PAGO:".
- **Cálculo:** recalcula el préstamo a `date()` (L94-L107).

### 34. Recibo en cuarto de página (Epson)
- **Fuente:** `ventas/pre_impr_re5.PRG` (`for_rec=5`).
- **Campos:** encabezado; título con "NO."; "Fecha", "Contr.#"; receptor; "LA SUMA DE:"; "CONCEPTO:"; "BALANCE PENDIENTE:"; "RECIBIDO POR".
- **Errores:** alias inexistente `a.dir` (L67); variable mal escrita `mtitre` (L43).

### 35. Recibo en cinta (Star)
- **Fuente:** `ventas/pre_impr_re6.PRG` (`for_rec=6`).
- **Campos:** encabezado, hora, "RECIBO DE INGRESO", "PRESTAMO No.:", "RECIBO No.:", "NCF:", "Fecha:", "HEMOS RECIBIDO DE:", "LA SUMA DE: RD$", "CONCEPTO:", "Recibido por".

### 36. Recibo, NC o ND en texto (matriz)
- **Fuente:** `ventas/pre_impr_re2.prg` (`confpre.rec=2`, pre_pago.PRG L278-L279).
- **Campos:** encabezado; título según tipo; número; receptor; "LA SUMA DE: RD$"; "CONCEPTO:"; "Aprobado Por"; "***** Siempre A Sus Ordenes *****".
- **Nota:** pre_config rotula la opción "2 = Con Balance", pero este formato no imprime balance.

### 37. Nota de Crédito (FRX)
- **Fuente:** `ventas/pre_impr_nc.FRX` (pre_impr_rec L41-L46).
- **Campos:** compañía, NCF, "NOTA DE CREDITO", "FECHA:", "PRESTAMO NO.:", "NC NO.", "NOTA DE CREDITO A:", "RNC/CEDULA:", "LA SUMA DE:" "RD$", "POR CONCEPTO DE:", forma de pago, "TOTAL =", "CAJERO".

### 38. Nota de Débito (FRX)
- **Fuente:** `ventas/pre_impr_nd.FRX`. Mismo diseño con "NOTA DE DEBITO", "ND NO.", "NOTA DE DEBITO A:".

### 39. Recibos y notas en modo administración
- **Fuente:** `ventas/pre_impr_reb.prg`, `pre_impr_ncb.PRG`, `pre_impr_ndb.PRG` (si `confpre.adm='S'`, pre_pago.PRG L267-L276).
- **NC/ND:** membrete del bufete fijo; "Hemos acreditado/debitado a {cliente} la suma de RD$ … por concepto de …, concerniente al préstamo consentido en esta oficina por {acreedor}." (ncb L39-L106).
- **Recibo (reb):** pide "Tipo de Pago Abono/Cuota/Interés/Saldo (A/C/I/S)", número de cuota, período, "Imprimir Liquidación (S/N)", "Observación" (L60-L66) y llama a `pre_impr_rab/rcu/rin/rsa` (L76-L83).
- **Errores:** esos cuatro programas están vacíos (solo `return`): en modo administración no se imprime recibo de pago. `pre_impr_ndb.PRG` L52 dice "NOTA DE CREDITO NO." en una nota de débito.

### 40. "RECIBO DE DESCARGO" (liquidación al acreedor)
- **Fuente:** `ventas/pre_liqpag.PRG`.
- **Contenido** (L53-L137): "ASUNTO: Liquidación de ingreso sobre préstamo hipotecario" y "ESTADO DE CUENTA": "Balance del Capital Adeudado al Momento del Pago", "Total Ingresado a Esta Oficina", "Abono a Capital"/"Saldo de Capital", "Pago de interés", "Mora para el Acreedor", "Comisión por Administración", "Mora por Administración", "Balance del Capital Adeudado Después del Pago", "Total para la Oficina" (com+moc), "Total a Entregar al Acreedor" (cap+int+mor), "ACUSE DE RECIBO".
- **Cálculo:** en un saldo, el interés se reparte acreedor/oficina en proporción `int/(int+com)` (L27-L32).
- **Nota:** solo lo llaman ncb/ndb cuando `tip='P'` (ncb L113-L115), algo que nunca pasa en una NC o ND: es código muerto.

### 41. Intimación de pago (RTF)
- **Fuente:** `ventas/pre_imp_intim.PRG` con `intimacion-simple.rtf` e `intimacion-guardian.rtf` (en el repo están en `ventas/`; el programa las busca en `config\`). Se dispara desde Balance de Cuotas.
- **Marcadores** (L77-L86): nombre_cliente, cedula_cliente, direccion_cliente, monto_prestamo (`ncu*cuo+adi`), monto_vencido_sin_mora (`mmonven−mbalmor`), fecha_prestamo, fecha_vencimiento (`gomonth(fec,ncu)`), cantidad_cuotas, monto_cuota, garantia_prestamo.
- **Errores:** usa el cursor `prestamo` y no `prestamo2`, y asume que todo préstamo es mensual (L47-L56).

### 42. Reimpresión de recibos ("Accesorios")
- **Fuente:** "1.- Reimprimir Recibos de Préstamos" (`ventas/pre_reimrec.PRG/.SCX`: "Recibo/ND inicial"/"Recibo/ND Final") y "6.- Reimprimir Recibos por tipo de préstamos" (`ventas/pre_reim_rtp.PRG/.SCX`: "Tipo de Préstamos", "Fecha de los Pagos", "Fecha Final").
- **Funcionamiento:** reusa los formatos 31-38 por cada pago del rango (pre_reimrec L41-L73; pre_reim_rtp L21-L55).
- **Nota:** el rango por `cod` también incluye NC (+100000000) y ND (+200000000) (pre_pago.PRG L391-L396).

---

## C. Menú "9.-Inversiones" (`ventas/pre_menuinv.prg`)

### 43. "8.- Estado de Cuenta de Inversión"
- **Fuente:** `ventas/pre_estinv.PRG` (TXT) y `.SCX`.
- **Filtros:** "Acreedor", "Fecha Inicial", "Fecha Final", "Imprimir".
- **Encabezado** (L379-L400): "Acreedor", "Dirección", "Cap. Disponible", "Interés … % Mensual", "Fecha 1er Dep.".
- **Columnas:** "FECHA", "OPERACION" (Depósito, Ret. Cap., Int. Gan., Nota Cre., Ret. Int., Nota Deb., Nueva Tasa), "DEPOSITOS", "RETIROS", "BAL/CAPITAL", "BAL/TOTAL", "CONCEPTO".
- **Resumen:** con `madminist='T'` (L198-L233): "Total Entregado para Invertir", "Menos Ret. Personales de Capit", "Capital Restante", "Intereses Ganados", "Mora Ganada", "Intereses + Mora Ganados", "Menos Ret. Personal de Interés", "Menos Intereses Reinvertidos", "Intereses Restantes", "Total Retiro para Uso Personal", "Balance en Libreta Bancaria", "Capital Prestado Sin Cobrar", "Balance General". En otro caso (L235-L255): "Total invertido", "Capital por Cobrar", etc.
- **Cálculo:** compuesto mensual (`capitaliz`, varios.PRG L2244-L2297) si `cap='S'`; si no, simple sobre el capital con meses de 30 días (`acumulado`, L2300-L2365). Fuera del modo administración desglosa mes a mes (`desgl_int`, L326-L370).

### 44. "9.- Reporte de Inversiones" ("Reporte de Inversionistas")
- **Fuente:** `ventas/pre_repinv.PRG` (TXT) y `.SCX`.
- **Filtros:** "Inversiones capitalizables/No capitalizables/Todas (S/N/T)", fechas, "Calcular Intereses Hasta", "Tipo de inversiones", "Clase de inversiones", "Acreedor", "Incluir inversiones con balance en cero (S/N)", "Recalcular inversiones hasta", "Imprimir".
- **Columnas** (L45): "INVERSION #", "ACREEDOR", "TELEF.", "CAPIT.DISP.", "TASA(%)", "INT. MENSUAL" (`capit*int/100`), "INT. ACUM." (`bal−capit`), "BALANCE".
- **Totales:** acreedores, capital, interés mensual, interés acumulado y balance (L147-L156).

### 45. "A.- Reporte de Pagos a Inversionistas"
- **Fuente:** `ventas/pre_reppaginv.prg` (TXT) y `.SCX`.
- **Filtros:** fechas (`fep`), "Incluir retiros de capital", "Incluir retiros de interés", "Acreedor", "Incluir Recibos Cancelados"/"NO Cancelados".
- **Columnas** (L54): "CLIENTE", "INVERSION#", "FECHA", "OPERACION" (Ret. Cap./Ret. Int.), "MONTO", "RECIBO#", "Concepto:".
- **Totales:** "Pagos" y monto (L107-L109).

### 46. "D- Reporte de las Operaciones de las Inversiones"
- **Fuente:** `ventas/pre_repopeinv.PRG` (TXT) y `.SCX` ("Reporte de Operaciones").
- **Filtros:** incluir depósitos, retiros de capital, intereses ganados, retiros de interés, NC, ND, cambios de tasa; "Desde"/"Hasta"; recibos cancelados/no cancelados.
- **Columnas** (L98): "FECHA", "INVERSION#", "DOCUMENTO#", "ACREEDOR", "OPERACION", "MONTO".
- **Totales:** "Operaciones" y suma de MONTO (L175-L179).
- **Error:** suma depósitos, retiros y tasas (`ope='T'`) en un solo total sin sentido contable.

### 47. Recibo de depósito o ingreso de inversión
- **Fuente:** `ventas/pre_imprdep.PRG/.FRX`, desde `pre_paginv.PRG` L124-L126.
- **Campos:** compañía, "R.N.C.", "Tel.", tipo de operación; "FECHA:"; "INVERSION No."; "RECIBO No."; "HEMOS RECIBIDO DE:"; "LA SUMA DE:" "RD$"; "POR CONCEPTO DE:"; "TOTAL ="; "Entregado Por"/"Recibido Por"; "ESTE RECIBO NO ES VALIDO SI NO ESTA FIRMADO Y SELLADO"; "GRACIAS POR PREFERIRNOS".

### 48. Recibo de retiro de inversión
- **Fuente:** `ventas/pre_imprret.FRX`. Mismo diseño con "HEMOS PAGADO A:". Existe además "2.- Reimprimir Recibos de Inversiones" (`ventas/pre_reirecinv.prg`).

---

## D. Reportes relacionados de otros módulos

### 49. Cuadre de caja de cooperativa
- **Fuente:** `ventas/repcuaca.PRG` (formato 9, L71-L119 y L158-L161) + `ventas/repcua_coop.PRG` + `ventas/papeleta2.SCX` (conteo de billetes) + `ventas/REPCUA_COOP.FRX`. Está en el menú de cuadres de Ventas.
- **Contenido:** "CUADRE DE CAJA DEL CAJERO: …"; "VALORES ESTREGADOS" [sic] (efectivo, cheque, tarjeta, total entregado); "MONTO COBRADO", "FONDO INICIAL", "SUBTOTAL", "RETIRO AHORROS/CERTIFICADOS/ACCIONES", "EGRESOS", "TOTAL A ENTREGAR", SOBRANTE o FALTANTE; conteo de "BILLETES" de DOS MIL a UNO; tabla "RENGLON/EFECTIVO/CHEQUE/TARJETA/TOTAL" con 'Préstamos', 'Ahorros', 'Certificados', 'Acciones' y los servicios, con totales.
- **Cálculo:** pagos de préstamo repartidos por `cht` (C cheque, T tarjeta, el resto efectivo) (repcua_coop L21-L34); inversiones según `invers.tip` (1 ahorro, 2 certificado, 3 acciones) (L40-L93).
- **Error:** filtra por `fec` (intereses hasta) y no por `fep` (fecha real) (repcuaca L90-L94).

### 50. Préstamos a empleados (Nómina)
- **Fuente:** `ventas/n_rep_pre.PRG/.SCX/.FRX`, sobre `config.bdnomina.prestamo` (instalar/bd_nom.sql L167-L171).
- **Filtros:** forma de pago, departamento, tipo, clase, fechas, empleado.
- **Columnas:** "NOMBRE", "FECHA", "MONTO", "BALANCE" (monto − deducciones hasta hoy, L95-L117).
- **Totales:** "Empleados", monto y balance.
- **Alcance:** préstamo interno sin interés; no es parte del producto financiero.

### 51. Cheques futuristas
- **Fuente:** `ventas/che_fut.PRG/.SCX/.FRX` (DBF local; lo usa `repcuac3`).
- **Columnas:** "CLIENTE", "CHEQUE NUM.", "FECHA/CUADRE", "FECHA/DEPOSITO", "MONTO". Totales: "CHEQUES" y monto.
- **Alcance:** cheques posfechados de Ventas. En préstamos no existe ese control: solo el código `cht='C'`.

---

## Anexo A. FRX revisados que no son del módulo
- `impr_che.FRX`, `impr_c02/c03/c04/c99.FRX`: impresión de cheques (Bancos).
- `impr_sol.FRX`: "SOLICITUD DE CHEQUE" (Bancos), no de préstamo.
- `impr_rec.FRX`, `impr_rrr.FRX`: recibos de cuentas por cobrar de Ventas.
- `repcuaca.FRX`, `rep_cua.FRX`, `rep_lect.FRX`: cuadres y lecturas de Ventas.
- `estsit1.FRX`: estado de situación.
- `N_ESTEMP.FRX`, `n_repliq.FRX`: Nómina.
- `pack_li2.FRX`: lista de empaque.
- `lis_pre*.FRX`: listas de precios de inventario ("pre" = precios, `lis_PRE.PRG`).

## Anexo B. Lo que no se pudo decodificar o no existe
- No hay reporte de solicitud de préstamo: `pre_edit_sol.SCX` "Imprimir" tiene `*REPORT FORM pre_impr_sol` comentado y ese FRX no existe.
- "Estadísticas de Préstamos" no está implementado.
- `pre_impr_rab/rcu/rin/rsa` están vacíos.
- `pre_paga_mul.FRX` solo tiene campos; el texto del pagaré estaba en el papel.
- De los RTF solo revisé los marcadores, no el texto legal.
- No encontré `.FXP` de reportes sin su `.PRG`.
- `TAG` de los FRX (Epson LX-300, HP LaserJet M1120) son metadatos de impresora.
````

---
