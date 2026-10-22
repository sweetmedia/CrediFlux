# SEANE — Auditoría del módulo financiero y comparación con CrediFlux

> SEANE: rutas relativas a `SEANE/sis-sql/` (VFP 9 sobre PostgreSQL vía SQLEXEC; esquema en `config.bdprestamo`). CrediFlux: rutas relativas a `CrediFlux-v2/`. "L" = línea.
> Inventario de reportes: ver `REPORTES_FINANCIEROS.md`. Fecha: 2026-10-21.

## 1. Arquitectura general de SEANE (préstamos)

- Escritorio en Visual FoxPro. Los formularios `.SCX` llaman a programas `.PRG`. La lógica de cálculo está concentrada en `ventas/varios.PRG` (3.790 líneas).
- Los datos viven en PostgreSQL en el esquema `bdprestamo` (`instalar/bd_pre.sql`). Los clientes son la tabla compartida con Ventas `cliente` (`instalar/bd_cli.sql` L3-L43). Deudor, fiador y acreedor son todos registros de `cliente`.
- Cada operación trae los datos a cursores locales (`prestamo2`, `cuota2`, `pago2`), recalcula en arreglos públicos en memoria (`arfec`, `arcap`, `arint`, `arcom`, `armor`, `armoc`, `artip`, `arcla`, `arcuotas`) y reescribe la tabla `cuota` completa (varios.PRG L3440-L3480).
- El SQL se arma concatenando texto con dollar-quoting `$$…$$` (por ejemplo varios.PRG L2780). No hay transacciones.

## 2. Modelo de datos

### 2.1 `prestamo`: cabecera del préstamo (bd_pre.sql L36-L78)

**Identificación y personas**
- `cod` c(10): número del préstamo, rellenado con ceros (pre_prestamo.SCX Text1.Valid).
- `ref1`, `ref2`: "Referencia #1/#2".
- `cli`: deudor → `cliente.cod`. `fia`: fiador → `cliente.cod`. `inv`: acreedor o inversionista → `cliente.cod`.

**Estado y tipo de cálculo**
- `est`: 'A' activo, 'I' saldado (varios.PRG L3494-L3500).
- `tca`: tipo de capital, F fijo o V variable (francés).
- `tin`: tipo de interés, F sobre el monto original o V sobre el saldo ("Amortizado").
- `tco`: tipo de comisión, F o V.
- `tcu`: tipo de cuota, 'C' "Capital + interés" o 'I' "Interés Solamente" (pre_prestamo.SCX Init).
- `fpa`: frecuencia D/I/S/Q/M. El combo ofrece también 'A' Anual, pero la validación la rechaza (`$ 'DISQM'`, Combo1.Valid).
- `tga`: garantía P Prendaria, H Hipotecaria, S Solidaria, O Otra.
- `tip` (FK `tipopre`) y `cla` (FK `clasepre`): tipo y clase configurables (L257-L261). En los tickets `tip` también se usa como código de cobrador o proyecto.

**Fechas**
- `fec`: fecha del préstamo. `pa1`: fecha del primer pago. `fuc`: último cálculo de interés. `fup`: último pago.

**Montos y tasas**
- `mon`: capital.
- `int`: tasa de interés por período; `com`: tasa de comisión por período; `mor`: tasa de mora por período. Todas `numeric(12,7)`.
- `ncu`: número de cuotas. `cuo`: monto de la cuota.
- `pgc`/`gac`: % y monto de "Gastos de Cierre". `pog`/`oga`: % y monto de "Otros Gastos", que la página 1 de la pantalla llama "Cierre". `hon`: "Honorarios". `gal`: "Gastos Legales".
- `pac`: total pagado acumulado.
- `factura`: número de factura cuando el préstamo nace de una venta financiada (`fin_fac.PRG`).
- `val_gar`: "Valor/Garantía". `gar` (text): descripción de la garantía.
- `adi`: suma del capital de las cuotas adicionales (`cuo_ir`).
- `meses_int`, `int_prev`, `com_prev`, `per_ins`: meses de solo interés, sus tasas y el período donde se insertan.
- `usu`: usuario que grabó.

**Campos sin respaldo:** la pantalla tiene `tipo_mora`, `fpa_mora` y `mora_fija_diaria` ("Tipo de mora" P/F, "Forma/Mora", "Monto Fijo") en pre_prestamo.SCX. No existen en el esquema y ningún cálculo los usa: un grep en `ventas/` solo los encuentra en `pre_prestamo.SCT`.

### 2.2 `cuota`: tabla de amortización viva (L80-L92)
- `pre` → `prestamo.cod`.
- `tip`: 'C' cuota normal o 'D' débito.
- `cla`: ' ' normal, 'I' irregular o adicional, 'A' incremento de capital.
- `fec`: vencimiento. `fuc`: fecha hasta la que se calculó la mora o el interés.
- `cap`, `int`, `mor`, `com`, `moc`: **saldo pendiente** de cada componente (no el original).
- `mon`: monto original de la cuota.

### 2.3 `cuo_ir`: cuotas adicionales o irregulares (L95-L103)
- `pre`, `fec`, `cap`, `int`, `mor`, `com`, `moc`. Se capturan en "PAGOS ADICIONALES" (`pre_cuo_ir.SCX`) y se intercalan en `cuota` como `tip='D', cla='I'` (`gua_tab_amo`, varios.PRG L3204-L3262). Sirven para cuotas extraordinarias o balloon sin interés propio.

### 2.4 `pago`: recibos, notas y cambios de tasa (L106-L140)
- `cod`: número. Los recibos usan una secuencia; las NC suman 100000000 y las ND 200000000 (pre_pago.PRG L391-L396).
- `ncf`: comprobante fiscal (det_ncf L403-L449).
- `cli`, `pre`.
- `tip`: P recibo, C nota de crédito, D nota de débito, T cambio de tasa de interés, M cambio de tasa de mora.
- `cla` en un recibo: A abono a capital, C cuota, I interés + mora, M mora, S saldo. En una NC tiene los mismos códigos como tipo de descuento. En una ND: A aumento de capital, C cargo, I adicional que mueve las fechas (pre_pago.PRG L94-L106, L538-L581).
- `cht`: forma de pago, E/C/T/D (pre_pago.SCX Init).
- `est`: ' ' vigente o 'C' anulado.
- `fec`: "Intereses Hasta" (la fecha que se usa para calcular mora e interés). `fep`: fecha real del pago.
- `mon`: monto. Para T y M guarda la tasa nueva.
- `cap`, `int`, `mor`, `com`, `moc`: cómo se distribuyó.
- `bal`: balance real después del pago. `bca`: balance de capital.
- `c1..c4`/`cm1..cm4`, `c_otr`, `c_mora`: distribución manual por pagaré (solo en el formato OCHOHNOS).
- `con`: concepto. `forpag`: forma de pago en texto libre. `hora`, `usu`, `usuario`.

### 2.5 Inversiones (L142-L178)
- `invers`: una cuenta de ahorro, certificado o acciones (`tip` '1', '2', '3', varios.PRG L2379-L2387). Campos: `cap` (capitaliza S/N), `est`, `fec`, `fuc`, `fup`, `pa1`, `vence`, `mon` (depósito inicial), `capit` (capital vigente), `bal` (capital más intereses), `inti` (tasa inicial), `int` (tasa vigente, % mensual).
- `paginv`: operaciones sobre la inversión. `ope`: D depósito, R retiro de capital, I interés ganado, Y retiro de interés, + NC, - ND, T tasa. `cla`: EI, RP o vacío. También `cht`, `est`, `cod`, `inversion`, `inv`, `fec`, `fep`, `mon`, `capit`, `bal`, `con`, `usu`.

### 2.6 Otras tablas
- `solicitud` (L180-L249): datos laborales; ingresos; balance personal con activos corrientes, activos fijos, pasivos y capital; gastos del hogar; datos del cónyuge, padres y un familiar; `est` (Aprobar S/N); `concl` (conclusión). **No tiene ninguna relación con `prestamo`.**
- `llamada` (L251-L255): `cli`, `fec1` (fecha de la llamada), `fec2` (volver a llamar), `obs`.
- `confpre` (L3-L34): parámetros generales y cuentas contables (ver 9 y 10).
- `unos` (instalar/bd_ven.sql L144-L175): usuarios con cadenas de permisos `prestamo_gen`, `prestamo_rep`, `prestamo_inv` y `prestamo_acc`.

### 2.7 Relaciones
- `prestamo.cli`, `fia` e `inv` apuntan a `cliente.cod`.
- `cuota.pre`, `cuo_ir.pre` y `pago.pre` apuntan a `prestamo.cod`.
- `paginv.inversion` apunta a `invers.cod`; `invers.inv` a `cliente.cod`.
- El préstamo se relaciona con el inversionista solo a través de `prestamo.inv`, y la primera cuenta `invers` del acreedor se toma por `order by s` (varios.PRG L3359).
- No hay claves foráneas declaradas ni borrado en cascada controlado.

## 3. Ciclo de vida del préstamo

1. **Solicitud.** Menú "B.- Solicitud de Préstamo" (`pre_solicitud.PRG`, `pre_edit_sol.SCX`). Se captura la ficha y se marca "Aprobar Solicitud (S/N)". No crea el préstamo, no lo enlaza y no se puede imprimir (el reporte está comentado). Se puede borrar físicamente (pre_edit_sol Command3, `delete from solicitud`).
2. **Aprobación.** No existe como estado del préstamo. El préstamo nace activo (`est='A'`, `asie_pre` L3286). La única "aprobación" es el permiso por letra del menú.
3. **Alta y desembolso.** Menú "2.-Préstamos" (`pre_prestamo.SCX`).
   - Valida campos (Command1.Valid), recalcula la tabla (`calc_cuo`) y permite sobrescribir el monto de la cuota (ver 4.6). Graba con `asie_pre` (L3265-L3387), que reescribe `cuota` desde cero (`gua_tab_amo`).
   - En modo administración retira el capital de la cuenta del acreedor (L3352-L3384) e imprime el comprobante y el plan.
   - Si existe `config\pagare.rtf` genera el pagaré en Word.
   - El asiento contable del desembolso está comentado (pre_prestamo.SCX Command1.Valid: `*      do pre_contab with 'PRESTAMO'…`).
   - Los gastos `gac+gal+hon+oga` se restan para mostrar "RESTAN PARA EL CLIENTE" (pre_prestamo Page2), pero el sistema no registra el desembolso en caja ni en banco.
   - Un préstamo también puede nacer de una venta financiada (`fin_fac.PRG` L73-L150, código = número de factura). Si ya existía un préstamo con ese código, lo borra junto con sus cuotas, pero deja los pagos huérfanos (L122-L133).
4. **Cobro.** "3.-Recibos de Ingreso" → `pre_pago.PRG` con 'P'. Ver 5. Existen además pagos automáticos masivos (Accesorios "7.- Pagos Automáticos de la próxima Cuota", `pre_pago_aut.PRG`), que registran como pagada la próxima cuota de cada préstamo de un tipo **sin que entre dinero**.
5. **Ajustes.** "4.-Nota de Débito", "5.-Nota de Crédito", "6.-Cambiar Tasa de Interés", "7.-Cambiar Tasa de Mora" (`pre_pago.PRG` con D/C/T/M).
6. **Modificación o recálculo.**
   - Para modificar un préstamo hay que volver a teclear su número en "2.-Préstamos" (requiere permiso '5' de `prestamo_acc`). Al grabar se regeneran las cuotas sin los pagos aplicados.
   - "4.- Modificar Recibos/Ingreso" (`pre_modipag.prg`, `pre_modipag2.SCX`) permite editar en una grilla todos los campos de los recibos, anularlos o recuperarlos, y recalcular el préstamo reaplicando los pagos (`pre_recalpre.PRG`). También ofrece recalcular "TODOS" los préstamos.
   - La opción de accesorios "5.- Modificar Préstamos" está vacía (`pre_menuacc.PRG` L84-L85).
7. **Cierre.** Automático: cuando el balance por cuotas llega a 0, `est='I'` (varios.PRG L3494-L3500). Con un pago "S" se fuerza el saldo: las cuotas se ponen en cero y el préstamo se marca saldado (L3501-L3509). Borrar un préstamo elimina físicamente préstamo, cuotas, adicionales **y pagos** (pre_prestamo.SCX Command3, permiso '6'). No hay castigo (write-off) ni estado legal; el estado "CASTIGADO" de DataCrédito es solo una etiqueta del reporte.

## 4. Lógica de amortización (`calc_cuo`, varios.PRG L2011-L2126)

### 4.1 Fechas (`proxfec`, L1959-L2008)
- D: +1 día. I (interdiario): +2. S: +7.
- Q: +15 si `confpre.qui='V'` (quincenas variables). Si son fijas, se calculan dos días ancla por mes a partir de `pa1` (15/30, 16/1, etc.).
- M: `gomonth`. Si el mes no tiene ese día se usa el último día.
- En las cuotas mensuales cada fecha es `gomonth(arfec(1), i−1)` (L2029-L2030), así que no se acumula el desfase.

### 4.2 Combinaciones tca/tin/tco

Notación: P = `mon`, n = `ncu`, i = `int/100`, c = `com/100`, S = saldo de capital antes de la cuota.

| tca | tin | tco | Capital por cuota | Interés por cuota | Comisión por cuota | Ref. |
|---|---|---|---|---|---|---|
| V | V | V | francés sobre (i+c): cuota = `payment(P, i+c, n)`; cap = cuota − S·(i+c) | cuota − cap − com | S·c | L2040-L2049 |
| V | V | F | francés solo sobre i | cuota − cap | P·c fija (se suma a la cuota) | L2050-L2059 |
| V | F | V | francés solo sobre c | P·i fijo | cuota − cap | L2060-L2068 |
| V | F | F | **ningún caso coincide**: cap = int = com = 0 | 0 | 0 | L2038-L2069 |
| F | F | F | P/n | P·i (flat) | P·c | L2070-L2085 |
| F | F | V | P/n | P·i | S·c | ídem |
| F | V | F | P/n | S·i (saldo insoluto, capital fijo; "alemán") | P·c | ídem |
| F | V | V | P/n | S·i | S·c | ídem |

- La pantalla fuerza `tca='F'` cuando tin=F y tco=F (pre_prestamo Combo3/Combo4 LostFocus y Combo5.When). La combinación V/F/F solo puede entrar por código: `fin_fac.PRG` L96 asigna tca=tin=tco.
- Después del cálculo:
  - El capital se redondea a 2 decimales y la diferencia contra P se pasa a la última cuota (`arcap(n) += P − Σcap`) **y se resta del interés de esa misma cuota** (L2095-L2103). La cuota total queda igual, pero el interés de la última cuota cambia. En el caso V/F/F esto deja el capital de la última cuota en P y su interés en −P.
  - Al final cada capital se **trunca**: `int(arcap*100)/100` (L2121). Interés y comisión se redondean.
- **Solo interés (`tcu='I'`)** (L2013-L2016, L2104-L2111): una sola cuota "rodante" con todo el capital. En `carga_cuo` (L2558-L2605), si la fecha de corte pasa el vencimiento, se generan nuevas cuotas de interés (`P·i`, `P·c`) una detrás de otra hasta cubrir la fecha, y el capital se mueve a la última. Es un préstamo de interés perpetuo hasta que se abone el capital. El interés en curso se prorratea por días (`/mdivis`, con divisor 1, 2, 7, 15 o 30).

### 4.3 Gastos y comisiones
- `oga` ("Cierre"/"Otros Gastos") se **financia**: se reparte en partes iguales y se suma al **interés** de cada cuota (`mint_cie = oga/n`, L2088-L2093).
- `gac`, `gal` y `hon` no entran a las cuotas. Solo se restan para mostrar "RESTAN PARA EL CLIENTE" = `mon − gac − gal − hon − oga` (pre_prestamo Page2). Ojo: `oga` se resta del desembolso **y además** se cobra en las cuotas (ver riesgos).
- La comisión (`com`) es un cargo financiero periódico. En el modo administración pertenece a la oficina y el interés al acreedor (pre_liqpag L114-L117).
- **Seguro:** SEANE no tiene campo ni cálculo de seguro. Si se cobraba, era como cuota adicional ("Otros") o como nota de débito.

### 4.4 Meses de interés y período de gracia (`ins_mes_int`, L2129-L2180)
- Inserta `meses_int` cuotas de solo interés y comisión, con las tasas `int_prev`/`com_prev`, a partir del período `per_ins`. Desplaza las cuotas siguientes. El interés de gracia es P·int_prev (si tin=F) o el capital restante desde `per_ins` × int_prev (si tin=V).

### 4.5 Ajuste del interés de la primera cuota (`aju_cuo1`, L2183-L2211)
- Se activa con `confpre.int_rod_fe='S'` ("Variar Interés 1ra Cuota al Rodar Fecha de Pago"). Si `pa1` no cae exactamente un período después de `fec`, el interés y la comisión de la cuota 1 se recalculan: períodos completos × P·tasa más un tramo parcial capitalizado (`capitaliz`).

### 4.6 Cuota editada a mano
- Si el usuario cambia "Monto Cuota", la diferencia entre la cuota digitada y la calculada se **suma al interés de cada cuota** que tenga capital (pre_prestamo Text19.Valid y Command1.Valid; pre_recalpre.PRG L82-L95). Si la diferencia es exactamente 0,01 se agrega a la última cuota. Con esto se puede subir el interés efectivo sin dejar rastro.

## 5. Aplicación de pagos (`pre_pago.PRG` y varios.PRG)

1. **Situación al día** (`sit_pre`, pre_pago L478-L521): `est_pre` con fecha = "Intereses Hasta" (`pago2.fec`, editable por el usuario). Sugiere el saldo de la próxima cuota o, para `cla='S'`, el balance real. Avisa si el pago supera el balance, pero lo permite (`verimon`, L524-L535).
2. **Orden por clase** (pre_pago L153-L185; mismas reglas en pre_recalpre L211-L226):
   - `C` cuota (y por defecto): `aplpagcuo 'MOC,COM,MOR,INT,CAP'`. Recorre **cuota por cuota**, de la más vieja a la más nueva (incluye débitos y adicionales). Dentro de cada cuota paga en este orden: **mora de comisión → comisión → mora → interés → capital** (varios.PRG L3068-L3126).
   - `I` interés + mora: 'MOC,COM,MOR,INT' (no toca capital).
   - `M` mora: 'MOC,MOR'.
   - `A` abono a capital:
     - En préstamos de solo interés: orden completo.
     - En los demás: `aplpagcap` (L2999-L3065).
       - Si tin=V, se descuenta el abono del capital pendiente y se recalcula el interés de cada cuota sobre el nuevo saldo **conservando el monto de cuota**. Como el interés baja, cada cuota amortiza más capital y el plazo se acorta.
       - Si tin=F, se descuenta capital desde la **última cuota hacia atrás** y se eliminan el interés y la comisión de las cuotas que quedan en cero. El plazo se acorta.
     - En los dos casos la mora vuelve a su valor previo (`armorV`).
   - `S` saldo (código heredado; la pantalla solo acepta A/C/I/M, pre_pago.SCX Text4.Valid): se paga el capital y el resto se reparte entre interés y comisión en proporción `int/(int+com)`, más toda la mora acumulada. Todas las cuotas quedan en cero (pre_pago L198-L216; varios.PRG L3502-L3509). El interés no devengado se descuenta de forma implícita, porque se cobra el balance real y no el balance por cuotas.
3. **Redondeo:** cada componente distribuido se trunca a centavos. Lo que falte se suma primero a la **mora** (varios.PRG L3177-L3185) y luego, otra vez, al **interés** (pre_pago L224-L228).
4. **Fechas de cálculo:** cuando una cuota recibe pago, su `fuc` avanza a `pago2.fec`. Desde esa fecha se vuelve a calcular la mora (L3127-L3131).
5. **Persistencia:** `asie_pag_pre` (L3391-L3511) inserta el pago, reescribe todas las cuotas, actualiza `fuc`, `fup` y `pac` y fija `est`. Si `confpre.contab='S'` genera el asiento (pre_pago L233-L235). Imprime el recibo (L263-L286) y, en modo administración, registra en la cuenta del acreedor los movimientos D, R, I e Y del capital, el interés y la mora cobrados (`reg_ope_inv`, L289-L344).
6. **Numeración:** `max(cod)+1` según el tipo (L370-L400). El NCF se obtiene igual, buscando el máximo con `like` (L403-L449), con el formato antiguo de 11 caracteres de prefijo más 8 de secuencia. Dos cajas a la vez pueden obtener el mismo número.

## 6. Mora y recargos (`capit_cuo` L2611-L2682 y `capitaliz` L2244-L2297)

- **Base:** el saldo total vencido de la cuota, `cap+int+mor+com+moc`, desde `fuc` (último cálculo) hasta la fecha de corte. En préstamos de solo interés (cuotas no débito) la base excluye el capital (L2638-L2643).
- **Fórmula (compuesta):**
  - Por cada período completo de la frecuencia: `saldo += saldo × mor%`.
  - Por la fracción: `saldo × mor% × días/30` en mensual, o `días/divisor` con divisor 1, 2, 7 o 15 en las demás frecuencias.
  - El resultado se trunca a centavos.
  - Primero se lleva el cálculo hasta el próximo "punto ancla" alineado con `pa1` (L2263-L2281).
  - Resultado: **interés sobre interés y mora sobre mora**.
- **Sin días de gracia:** la mora corre desde el día siguiente al vencimiento. No hay parámetro de gracia.
- **Reparto:** la mora calculada se divide entre `mor` (acreedor) y `moc` (oficina) en proporción `(cap+int+mor)/(total)` (L2661-L2668). En préstamos de solo interés con la cuota en curso, se suma a `int`/`com` en lugar de a la mora (L2669-L2675).
- **Tasa:** `prestamo.mor`, que se puede cambiar con una operación 'M'. `selec_pre` toma siempre la última tasa T y la última M registradas (L2798-L2830).
- **Opciones de configuración que no hacen nada:**
  - "Redondear la mora (S/N)" (`confpre.red_mor`). Existe `redo_mor` (L2685-L2691), que redondea hacia arriba a múltiplos de 5, pero nadie la llama.
  - "Tipo de Balance" (`confpre.tba`), que nunca se lee.
  - "Monto Fijo Diario" (`mora_fija_diaria`), que no existe en el esquema.

## 7. Refinanciamiento y renegociación

No hay un flujo de refinanciamiento. Los mecanismos que existen son:
- **Cambio de tasa de interés (`tip='T'`):** guarda la nueva tasa y llama `aplpagcap 0` (pre_pago L144-L148).
  - Si tin=V, calcula una nueva cuota fija `payment(capital pendiente, (tasa nueva + com)/100, cuotas restantes)` y reconstruye las cuotas (varios.PRG L3019-L3037).
  - Si tin=F, solo cambia el interés por cuota a `P × tasa nueva` (L3051-L3058).
- **Cambio de tasa de mora (`tip='M'`).**
- **Nota de débito con "Débito representa préstamo adicional al préstamo inicial"** (`cla='A'`): suma el monto al capital de la **última cuota** (`ubi_ND`, L2975-L2982). No recalcula cuotas ni intereses: es un balloon sin interés.
- **Nota de débito 'I':** inserta un cargo y corre las fechas de las cuotas siguientes un período (`ava_fec_cuo`, pre_pago L245-L260). Funciona como un diferimiento.
- **Notas de crédito A/I/M/S:** descuentos al capital, al interés y mora, a la mora, o para saldar (pre_pago L548-L565). Se aplican con el mismo orden que un pago y se contabilizan contra las cuentas "Descuentos de" (pre_contab L56-L65), pero solo si `cap>0` (pre_pago L648-L651).
- **Reconstrucción total:** `pre_recalpre.PRG` vuelve a generar la tabla con `calc_cuo` y reaplica todos los pagos no anulados en orden (L139-L265).

## 8. Fiadores y garantías

- **Fiador:** un solo fiador por préstamo (`prestamo.fia` → `cliente`). Aparece en el balance, el estado de cuenta, la lista de cobro, el plan, el pagaré con garante (`pagare_garante.rtf`) y el recibo re4 ("Y/O").
- **Garantía:**
  - Tipo `tga` (P/H/S/O). La "Solidaria" de hecho es el fiador.
  - `val_gar`, descripción libre en el memo `gar` (obligatorio si existe la plantilla de pagaré, pre_prestamo Command1.Valid) y el objeto o vehículo del pagaré (chasis, marca, placa, etc.), que solo vive en los parámetros de impresión.
  - No existe un registro de garantías con su estado (liberada, ejecutada).
  - Los reportes filtran "Garantía" comparando el campo memo `gar` con la letra (`gar=$$P$$`, pre_reppre L106-L108, PRE_repcxc L33-L35, etc.) en lugar de `tga`. Ese filtro no funciona.

## 9. Efectivo, cheques y caja

- **Forma de pago por recibo:** `cht` E/C/T/D (pre_pago.SCX) más el texto libre `forpag` (pre_pago3.SCX). No se guardan número de cheque, banco ni fecha de depósito. Los cheques posfechados solo existen en Ventas (`che_fut`).
- **Sin caja propia:** no hay apertura, cierre ni arqueo de caja en el módulo de préstamos. Los pagos de préstamo solo se cuadran en el "Cuadre de caja" de Ventas, formato 9 (cooperativa, repcua_coop.PRG), que separa efectivo, cheque y tarjeta por `cht` y cuenta billetes.
- **Contabilidad:** el asiento de pago debita siempre `confpre.efe` ("Efectivo en Caja y Bancos"), sin importar si se pagó con cheque o tarjeta (pre_contab L42-L48).
- **Desembolsos:** no generan salida de caja ni cheque desde este módulo.

## 10. Asientos contables (`pre_contab.PRG`)

Se activan con `confpre.contab='S'` ("Integrar con Contabilidad (S/N)"). Las cuentas se configuran en pre_config.SCX:

| Proceso | Débito | Crédito | Ref. |
|---|---|---|---|
| PRESTAMO (desembolso) | CxC Capital | Banco o caja (cuenta pedida al usuario) | L39-L41 (la llamada está **comentada** en pre_prestamo y fin_fac) |
| PAGO | Efectivo, por el total | CxC capital, CxC interés, CxC comisión, CxC mora (mor+moc) | L42-L48 |
| ND | CxC por componente | Banco o caja (cuenta pedida) | L49-L55 |
| NC | Descuentos de capital, interés, comisión y mora | CxC por componente | L56-L65 |
| ACUMULAR INTERESES GANADOS | CxC int/com/mor | Intereses, comisiones y mora ganados | L66-L93 (**`cal_int_mes` es un stub que devuelve ceros**, L134-L139) |
| DEPOSITO, RETIRO, INTERESES de inversión | Caja/CxP | CxP capital o interés / gasto de interés | L94-L128 (`cal_IxP_mes` vacío, L142-L143) |

- El modelo es de CxC por componente con ingreso reconocido al devengar. Pero el devengo nunca se ejecuta y el desembolso no se contabiliza, así que los saldos de CxC contables no cuadran.
- El asiento queda descuadrado si hay residuos de redondeo. No hay asientos de reverso cuando se anula un recibo (`est='C'`).

## 11. Usuarios y permisos

- **Tabla `unos`** (bd_ven.sql L144-L175): cada usuario tiene una cadena de letras por área: `prestamo_gen` (botones del menú principal 1-9, A, B, C), `prestamo_rep` (reportes), `prestamo_acc` (accesorios; además '5' permite modificar préstamos y '6' borrarlos, según pre_prestamo.SCX) y `prestamo_inv`. Las opciones se listan en `pre_per_gen.PRG`, `pre_per_rep.PRG`, `pre_per_acc.PRG` y `pre_per_inv.PRG`.
- **Elevación por clave** (`pide_clave`, ventas.PRG L1183-L1215): si el usuario no tiene la letra, otro usuario puede escribir su clave para autorizar la operación.
- **Hash de clave:** `chr(((asc % 9)*17) % 128)` (L1200-L1207). Es reversible, con muchas colisiones y apenas unos 9 valores posibles por posición.
- **Auditoría:** solo `usu` en prestamo, pago e invers, y `hora`/`usuario` en pago. No hay bitácora de cambios: las ediciones de recibos y préstamos sobrescriben los datos sin dejar rastro.

## 12. Inversiones y modo administración (resumen)

- **`confpre.adm='S'` ("Administrar Dinero"):** la financiera presta dinero de inversionistas. Cada préstamo tiene acreedor (`inv`). El alta retira el capital de la cuenta del acreedor y cada cobro le acredita capital, interés y mora (`reg_ope_inv`). Si `prestamo.tip='P'` ("uso personal") se registra además el retiro inmediato.
- **Interés del inversionista:** compuesto mensual o simple con meses de 30 días (varios.PRG L2244-L2365). Se asienta como operación 'I' cada vez que hay movimiento (`intereses`, L2836-L2887).

---

## 13. Análisis de brechas (SEANE → CrediFlux)

Esfuerzo: S ≤ 3 días, M 1-2 semanas, L &gt; 2 semanas.

| # | Función de SEANE | ¿Existe en CrediFlux? (evidencia) | Esfuerzo | Recomendación |
|---|---|---|---|---|
| 1 | Flat (capital fijo + interés sobre el monto original) | **Sí.** `backend/apps/loans/views.py:933-960` (rama `else`, tasa mensual × meses) | — | Mantener |
| 2 | Saldo insoluto / alemán (capital fijo, interés sobre saldo) | **Parcial y con error.** `views.py:776-829` divide la tasa entre `periods_per_year` (12, 26, 52, 365; L791-L804), o sea la trata como anual. La calculadora (`views.py:2160-2172`, `_saldo_insoluto` L2212) y flat/francés (L852, L938) la tratan como mensual. `models.py:292` dice "Annual interest rate" | S | Arreglar ya. Unificar la semántica de tasa por período en un solo servicio que usen tanto la calculadora como la creación del préstamo, y agregar pruebas con los ejemplos de LOGICA_PRESTAMOS.md |
| 3 | Francés (cuota fija) | **Sí.** `views.py:831-887` | — | Mantener |
| 4 | Francés con comisión incluida (`payment(P, i+c, n)`) y comisión F/V separada | **No.** El Loan no tiene comisión (`models.py:259-412`) | M | Agregar `commission_rate` y `commission_type`, y un componente "comisión" en la cuota |
| 5 | Tasas con 7 decimales | **No.** `interest_rate` es `DecimalField(5,2)` (`models.py:288-293`) | S | Subir a 4-7 decimales para migrar tasas reales |
| 6 | Frecuencias D/I/S/Q/M y quincena fija 15/30 | **Parcial.** daily/weekly/biweekly/monthly/quarterly (`models.py:314-320`). No hay interdiario ni quincena fija. Las cuotas se aproximan como `term_months*4` o `*30` (`views.py:757-768`) | M | Guardar `num_installments` explícito; agregar `interdaily` y `semi_monthly` con días ancla |
| 7 | Gastos de cierre, legales y honorarios descontados del desembolso ("Restan para el cliente") | **Parcial.** Solo en la calculadora: `legal_fees` deducted/financed (`serializers.py:926-929`, `views.py:2167-2178`). No se guarda en el Loan | M | Modelo `LoanCharge` (tipo, monto, deducido o financiado) y desembolso neto. No repetir el doble cobro de `oga` |
| 8 | Gastos financiados repartidos en las cuotas (`oga/n` al interés) | **Parcial.** La calculadora suma lo financiado al capital | S | Financiarlos como capital o como cargo separado, nunca como "interés" |
| 9 | Cuotas adicionales o irregulares (`cuo_ir`) | **No** | M | Cuotas extraordinarias en el cronograma (`installment_type`) |
| 10 | Meses de gracia de solo interés insertados en el período X | **No** | M | Parámetros `grace_periods` y `grace_rate` en la generación del cronograma |
| 11 | Préstamo de solo interés con capital al final ("rodante") | **No** | M | Producto "interest-only/balloon" con vencimiento definido. Evitar el rodado perpetuo |
| 12 | Ajuste del interés de la 1ra cuota cuando el primer pago no es a un período | **No** (`views.py:769` usa `first_payment_date` sin ajustar el interés) | S | Interés prorrateado de la primera cuota, configurable por tenant |
| 13 | Cuota editada a mano (la diferencia se suma al interés) | **No** | — | **No portar.** Si se necesita redondeo comercial, usar una regla explícita y auditada |
| 14 | Orden de aplicación MOC→COM→MOR→INT→CAP, cuota por cuota desde la más vieja | **Parcial.** Mora→interés→capital pero sobre **una** cuota (`serializers.py:405-431`; sin cuota indicada, la vencida más vieja, L438-L474). El cronograma solo lleva `paid_amount` total (`signals.py:88-115`). El excedente se registra como `principal_paid` (L433-L434, L469-L471) aunque pague interés de las siguientes | M | Crear un ledger por cuota y componente (pagado de capital, interés, mora y comisión en cada cuota) y un motor de aplicación con orden configurable que reparta entre todas las cuotas vencidas |
| 15 | Pago sin cuotas vencidas: interés sobre saldo | **Con error.** `serializers.py:478-485` calcula `outstanding_balance × tasa`, y `outstanding_balance` ya incluye los intereses futuros (`signals.py:148-154`) | S | Usar el capital pendiente |
| 16 | Abono a capital que reduce plazo (y opción de reducir cuota) | **No** | M | Acción `prepay_principal` con regeneración del cronograma restante (opciones de plazo o cuota) |
| 17 | Pago para saldar con descuento del interés no devengado ("Balance real") | **No.** No hay cotización de saldo | M | Endpoint de cotización (capital + vencido + devengado prorrateado + mora) y pago de cierre |
| 18 | Mora compuesta por período con tasa por préstamo | **Parcial y con errores.** Mora por tenant (`apps/tenants/models.py:52-91`) calculada en `management/commands/calculate_late_fees.py:97-140`. Compara 'per_day'/'per_week' contra choices 'daily'/'monthly'/'one_time' (L109-L116 vs tenants L78-L87), así que la diaria cae a "única". Devuelve `Money(0,'USD')` (L102, L143). Existe además `LATE_PAYMENT_FEE`/`GRACE_DAYS` en Constance (`config/settings/base.py:419-428`), que no se usa | S (errores) / M (por préstamo) | Arreglar las frecuencias y la moneda. Agregar tasa de mora y días de gracia por producto o préstamo. **Mora simple** sobre capital o cuota vencida, no compuesta |
| 19 | Reparto de la mora acreedor/oficina | **No** | L | Solo si se implementa el modo administración |
| 20 | Cambio de tasa de interés o de mora a mitad del préstamo | **No** | M | Evento `RateChange` con regeneración del cronograma pendiente y traza |
| 21 | Nota de crédito (descuento a capital, interés, mora o saldo) | **No** | M | `LoanAdjustment` (tipo crédito o débito, componentes, aprobación, motivo, e-CF 34 si aplica) |
| 22 | Nota de débito (cargo o aumento de capital) | **No** | M | Igual que 21. El aumento de capital debe regenerar las cuotas, no ir como balloon |
| 23 | Anular recibo con traza y recálculo | **Parcial.** `reverse` solo para el dueño (`views.py:1128-1164`). Pero `LoanPaymentViewSet` es ModelViewSet con `IsAuthenticated` (`views.py:997-1019`): cualquier usuario puede hacer PATCH o DELETE (el delete dispara el recálculo, `signals.py:178-182`). `cancel` pone `'cancelled'`, que no está en las opciones (`views.py:1123` vs `models.py:631-637`) | S | Bloquear update/destroy, reverso con motivo y AuditLog, y corregir el estado |
| 24 | Recálculo reaplicando pagos | **Sí.** `signals.py:27-131` (automático) | — | Mantener |
| 25 | Pagos automáticos masivos de la próxima cuota | **No** | — | **No portar** (registra pagos sin dinero). Si se quiere, usar domiciliación real |
| 26 | Solicitud con evaluación financiera (activos, pasivos, gastos) | **Parcial.** Loan `pending→approved/rejected` (`models.py:341-351`, `views.py:353-458`); Customer tiene empleo e ingresos (`models.py:60-85`). No hay balance personal ni conclusión | M | Modelo `CreditApplication` enlazado al Loan, con capacidad de pago |
| 27 | Fiador | **Sí, mejor.** `models_guarantors.py:10-95` (varios por préstamo, documentos) | — | Mantener |
| 28 | Garantía con tipo, valor y descripción | **Sí, mejor.** `Collateral` (`models.py:676-751`) con estado y metadatos de vehículo o inmueble | — | Mantener |
| 29 | Acreedor o inversionista por préstamo y modo administración | **No** | L | Solo si el negocio administra fondos de terceros. Fase posterior |
| 30 | Ahorros, certificados y acciones (inversiones) con interés compuesto o simple | **No** | L | Fuera del alcance de una financiera, salvo cooperativas. Evaluar aparte |
| 31 | Integración contable (asientos por componente, devengo) | **No** (no hay app contable) | L | Exportar asientos o integrar con un ERP. Definir cuentas en Constance o por tenant |
| 32 | NCF o e-CF en recibos | **Sí, mejor.** `apps/billing/models.py:138-160` (Invoice ligada a loan y payment, e-CF), `reports_dgii.py` (606/607) | — | Generar e-CF desde el pago donde aplique (el interés está exento, la comisión y la mora pueden llevar ITBIS: validar con contador) |
| 33 | Forma de pago (efectivo, cheque, tarjeta, depósito) | **Sí.** `models.py:621-629` + `reference_number` | — | Agregar banco y fecha para cheques si hace falta |
| 34 | Caja: arqueo, billetes, sobrante o faltante | **Sí, mejor.** `apps/cashbox/models.py:44` (CashSession), `:130` (CashMovement), `:204` (DenominationCount). **Pero los pagos no generan movimiento** (no hay `CashMovement.objects.create` en `apps/loans`) | S | Crear el CashMovement automáticamente al cobrar o desembolsar en efectivo dentro de una sesión abierta, y revertirlo al reversar |
| 35 | Llamadas de cobro y agenda | **Sí, mejor.** `models_collections.py:94-166` (resultado, promesa, próximo contacto, escalamiento) | — | Mantener |
| 36 | Carta de cobros e intimación | **Parcial.** Plantillas de contrato (`models_contracts.py`) y recordatorios por WhatsApp (`tasks.py`). No hay carta de intimación | S | Plantilla "intimación" en el motor de contratos con variables de vencido |
| 37 | Pagaré con plantilla | **Parcial.** Motor de contratos con variables (migración `0010`) | S | Agregar la plantilla de pagaré y la tabla de cuotas como variable |
| 38 | Plan de pagos impreso | **Sí.** `reports.py:25` LoanBalanceReport y `views.py:461` | — | Agregar firma por cuota y el desglose de comisión |
| 39 | Balance de cuotas y estado de cuenta por préstamo | **Sí.** `views.py:477` balance_report, `views.py:111` statement-pdf, `reports.py:662` | — | Agregar el estado detallado (cargos y pagos intercalados) |
| 40 | Recibo de ingreso impreso o ticket | **Sí.** `reports.py:403` PaymentReceiptReport | — | Formato ticket de 80 mm opcional |
| 41 | Reporte de préstamos con filtros (tipo, clase, garantía, frecuencia, fiador, saldados por rango, recálculo a fecha) | **Parcial.** `frontend/app/collections/reports/cartera/page.tsx:36-40` (solo la página 1 de préstamos activos, calculado en el navegador) | M | Endpoint de servidor paginado con filtros y exportación CSV/XLSX |
| 42 | Antigüedad de saldos 30/60/90/120/150/180 | **Parcial.** Buckets 0-7/8-30/31-60/60+ en el frontend (`vencimientos/page.tsx:45-48`, `cartera/page.tsx:57-62`) | M | Aging de servidor por capital y total, con cortes regulatorios |
| 43 | Cuentas por cobrar por componente | **No** | M | Depende del ledger del #14 |
| 44 | Ingresos por período con desglose capital, interés y mora, por cajero y hora | **Parcial.** `pagos/page.tsx:41-90` (página 1, sin rango de fechas en servidor) | S | Endpoint con rango, usuario y método, y exportación |
| 45 | Atrasos y lista de cobro con ticket por cliente | **Parcial.** `schedulesAPI.getOverdueSchedules` y `cuotas/page.tsx`. No hay ticket de cobrador | S | Reporte "ruta de cobro" por cobrador con ticket imprimible |
| 46 | Proyección de ganancias | **No** | S | Interés y comisión por devengar a partir del cronograma (excluyendo lo castigado) |
| 47 | Gastos por préstamo | **No** | S | Depende del #7 |
| 48 | Archivos para buró (DataCrédito, TransUnion/CICLA) | **No** (grep sin resultados) | M | Exportadores con el layout vigente de cada buró y reglas de estado |
| 49 | Exportación a Excel | **No** (los reportes son pantalla y `window.print()`) | S | CSV/XLSX en los endpoints de reportes |
| 50 | Tipos y clases de préstamo configurables | **Parcial.** `loan_type` con opciones fijas (`models.py:272-280`) | S | Catálogo de productos por tenant (tasas, frecuencias, cargos por defecto) |
| 51 | Permisos por opción y autorización por supervisor | **Parcial.** Roles (`apps/users/models.py:44-54`) y `CanApproveLoan`/`CanManageLoans` (`loans/permissions.py:8-72`). Pagos, cronogramas y garantías solo exigen `IsAuthenticated` | M | Matriz de permisos por acción y aprobación dual para ajustes y reversos |
| 52 | Castigo o estado legal | **Parcial.** Estados `written_off`/`defaulted` (`models.py:346-349`) y `LoanSchedule.written_off` | S | Flujo de castigo con asiento y motivo |
| 53 | Préstamos a empleados (nómina) | **No** | — | Fuera de alcance |

## 14. Plan de implementación priorizado

**Fase 0: corregir CrediFlux antes de portar nada (1 semana)**
1. Unificar la semántica de tasa (#2, #5). El riesgo de que la cotización y el contrato difieran es legal y comercial: el cliente firma un plan distinto al que se le cotizó.
2. Cerrar PATCH y DELETE de pagos, arreglar `cancel` y auditar el reverso (#23). Es un riesgo de fraude interno, igual al que tenía SEANE con `pre_modipag2`.
3. Arreglar las frecuencias y la moneda de la mora (#18), y el interés sobre `outstanding_balance` (#15).
4. Enlazar cobro y desembolso con la caja (#34).

**Fase 1: núcleo de cobro (3-4 semanas).** Es lo que una financiera dominicana usa todos los días y lo que vuelve confiables los reportes.
1. Ledger por cuota y componente con motor de aplicación configurable (#14). Base de las cuentas por cobrar, del aging, de los ingresos y de las notas de crédito.
2. Cotización y pago de saldo (#17) y abono a capital (#16).
3. Notas de crédito y débito con aprobación (#21, #22) y cambio de tasa (#20).
4. Mora por producto o préstamo con días de gracia, como mora simple (#18).

**Fase 2: reportes de servidor (2-3 semanas).** Antes eran el valor de SEANE; hoy en CrediFlux son pantallas que solo leen la página 1.
1. Reporte de préstamos con filtros y aging 30-180 (#41, #42), CxC por componente (#43), ingresos por período (#44), lista y ticket de cobro (#45), balance de cuotas y estado detallado (#39).
2. Exportación CSV/XLSX (#49) y luego DataCrédito y TransUnion (#48).

**Fase 3: producto (3-4 semanas).** Comisión periódica (#4), cargos de cierre guardados (#7, #8), frecuencias interdiario y quincena fija y número de cuotas explícito (#6), gracia (#10), solo interés con vencimiento (#11), cuotas extraordinarias (#9), interés prorrateado de la primera cuota (#12), catálogo de productos (#50).

**Fase 4: opcional según el cliente.** Solicitud con evaluación (#26), contabilidad (#31), modo administración e inversionistas (#29, #19), ahorros (#30), proyección (#46), gastos (#47), intimación y pagaré (#36, #37).

## 15. Riesgos: lógica de SEANE que NO se debe copiar

1. **Mora compuesta** (`capitaliz`, varios.PRG L2244-L2297, usada en `capit_cuo` L2611-L2682). Cobra mora sobre interés, mora sobre mora y mora sobre comisión, cada período. Es anatocismo; hay que validar con legal (Código Civil dominicano, art. 1154). CrediFlux debe usar mora simple sobre una base definida.
2. **Truncamiento sobre floats:** `int(x*100)/100` en L2121, L2296, L2676-L2680, L3023-L3024 y L3177-L3181. Pierde centavos por el error binario y siempre redondea hacia abajo. Los residuos se cargan a mora (L3182-L3185) y luego a interés (pre_prestamo L225-L227, pre_pago_aut L180-L182). Usar `Decimal` con redondeo bancario o half-up y una política explícita para el residuo.
3. **Diferencia de redondeo del capital descontada del interés de la última cuota** (L2102-L2103). En el caso tca=V/tin=F/tco=F, que ningún `case` cubre (L2038-L2069), genera cuotas en cero e interés negativo.
4. **Cuota digitada a mano que redistribuye la diferencia al interés de todas las cuotas** (pre_prestamo Text19 y Command1; pre_recalpre L82-L95). Manipula la tasa efectiva sin dejar traza.
5. **Modificar el préstamo regenera las cuotas** (`asie_pre`→`gua_tab_amo`, L3204-L3206) y deja los pagos sin aplicar hasta que alguien recalcula a mano.
6. **Borrados físicos:** préstamo con sus pagos (pre_prestamo Command3), recibos marcados en la grilla (pre_recalpre L354-L363), solicitudes, llamadas. Y `fin_fac.PRG` L127-L132 borra un préstamo existente dejando sus pagos huérfanos.
7. **Recibos editables en grilla sin auditoría** (pre_modipag2.SCX, 28 columnas) y anulación que no revierte el asiento contable.
8. **`UPDATE invers` sin `WHERE`** en `asie_pin` (L2902-L2903, L2905-L2906, L2940-L2944): cada movimiento de inversión (alta de préstamo o cobro en modo administración) pisa `fup`, `int`, `capit`, `bal` y `fuc` de **todas** las inversiones.
9. **Numeración `max()+1`** para recibos, NCF, préstamos, inversiones y solicitudes (pre_pago L370-L449, pre_prestamo Command3, pre_paginv L52-L58, pre_solicitud L54-L61). Hay carreras y duplicados con varias cajas a la vez.
10. **Reportes con errores** (no portar la lógica, solo la intención):
    - Aging con `m_60 WITH m_60` (pre_reppre L317) y detalle con variables de memoria (pre_reppre6 L26-L30).
    - Filtro de garantía sobre el memo (pre_reppre L106-L108 y en todos los reportes).
    - `DTOC(mrec_hasta)` sin formato ANSI (pre_reppre L113).
    - Las operaciones T/M se cuelan en ingresos (pre_reping1 L30-L31; pre_reping5 L14-L28).
    - CxC que incluye interés no devengado (PRE_repcxc L102-L103).
    - Cuadre por `fec` en vez de `fep` (repcuaca L90-L94).
    - Carta de cobros a préstamos sin atraso (pre_car_cob L56-L66).
    - Operaciones de inversión sumando tasas (pre_repopeinv L169-L171).
11. **Tasas guardadas con 2 decimales** aunque la columna admite 7 (asie_pre L3323-L3324; pre_paginv L108; pre_abrcuein L79-L80).
12. **`guarda_pag` mezcla campos:** guarda `c3=cm3` y `c4=cm4` y pierde `cm3`/`cm4` (pre_recalpre L345-L346). `completa_tabla` itera sin usar el índice (L406-L414).
13. **Código roto o muerto:**
    - `select pag` (pre_pago.SCX Combo2.Valid), `pago.c_otr`/`pago.mora` (pre_pago3.SCX), alias `a.dir` (pre_impr_re5 L67).
    - Recibos del modo administración vacíos (`pre_impr_rab/rcu/rin/rsa`), liquidación inalcanzable (ncb L113).
    - Devengo contable en stub (pre_contab L134-L143), desembolso sin asiento (pre_prestamo Command1), "Estadísticas" y "Modificar Préstamos" vacíos.
    - Opciones `red_mor`, `tba` y "mora fija" sin efecto.
14. **Datos de clientes escritos en el código:** bufete Lic. Benito A. Grullón (pre_cerprest L36-L43, pre_impr_ncb L39-L46, pre_liqpag L42-L48), Ochoa Hermanos con su RNC (pre_paga_8a.FRX), montos en dólares fijos (pre_imp_paga_word L92-L100), rutas `c:\terminal\…`.
15. **Seguridad:** hash de clave débil y reversible (ventas.PRG L1199-L1210); SQL armado por concatenación en todo el módulo; autorización por clave de terceros sin registro.
16. **Gastos de cierre `oga` cobrados dos veces:** se restan del desembolso ("RESTAN PARA EL CLIENTE") y además se financian como interés en las cuotas (calc_cuo L2088-L2093). Hay que confirmar con negocio, pero no se debe replicar.
17. **Préstamo de solo interés con rodado perpetuo** (carga_cuo L2580-L2604): genera interés indefinidamente sin vencimiento contractual. Mala práctica regulatoria.
18. **"Intereses Hasta" editable en cada recibo** (`pago2.fec`, pre_pago.SCX Text6): permite calcular la mora a una fecha anterior y condonar sin dejar rastro. En CrediFlux la fecha de cálculo debe ser la del pago, y las condonaciones deben pasar por notas de crédito aprobadas.
19. **Pagos automáticos sin dinero** (pre_pago_aut.PRG L90-L188): marcan cuotas como pagadas en lote.
20. **Prorrateo con divisor fijo:** 30 días para mensual aunque el mes tenga 28 o 31, y 15 para quincenal. Mezcla convenciones (`acumulado` usa 30/360 con parches para febrero, L2322-L2340). Definir una convención explícita por producto (Actual/365 o 30/360).
