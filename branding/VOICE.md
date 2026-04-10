# CrediFlux Voice & Copy Guide

How CrediFlux *talks* — to the gestor using the dashboard, to the
prospect landing on the marketing site, to the customer receiving a
WhatsApp reminder. Visual rules live in `DESIGN_SYSTEM.md`; this file
governs every word.

**Binding for all copy** in the landing, dashboard, blog, emails, push
notifications, WhatsApp templates, toast messages, error messages,
button labels, form hints, and empty states. Code comments and
technical docs (like this file) are not governed by it.

---

## 1. Who we talk to

Three audiences, in descending order of how often:

1. **El gestor** (loan officer / collections officer) — uses the
   dashboard 6–8 hours a day in a cooperative, microfinanciera, or small
   financial institution in RD. Hispanic, Spanish-native, middle class.
   Often mid-career, already comfortable with basic web apps but not a
   power user. Wants: less typing, fewer errors, faster decisions, clear
   visibility of who owes what.

2. **El dueño/gerente** de la financiera — evaluates CrediFlux to buy it.
   Wants: ROI clarity, trust signals, dominicano feel. Older than the
   gestor, sometimes less tech-comfortable but decides the budget.

3. **El cliente final** (borrower) — receives WhatsApp/email from the
   tenant via CrediFlux. Does not know CrediFlux exists. Wants: to
   understand his loan status, when to pay, how much. Might not read
   past the first line.

Write for #1 by default. Adjust for #2 on landing, `/precios`, and
sales-touching pages. Adjust for #3 on customer-facing templates only.

---

## 2. Core voice attributes

CrediFlux sounds:

| Attribute | Meaning | Example ✅ | Counter-example ❌ |
|---|---|---|---|
| **Directo** | Says what needs to be said, no preamble | "Guardado." | "¡Tu información ha sido guardada exitosamente!" |
| **Respetuoso** | Professional español RD, no slang, no jeringa gringa | "Préstamo creado" | "¡Yeah! Nuevo préstamo listo 🎉" |
| **Específico** | Uses names, amounts, dates | "Vence en 3 días — RD$4,500" | "Pago próximo" |
| **Cálido (cuando importa)** | Warm on onboarding, congrats, and empty states | "Aún no hay clientes. Empecemos por el primero." | "No data" |
| **Confiable** | Numbers right, ambiguity wrong | "Balance pendiente: RD$12,340.50" | "Más de 12k pendiente" |

Not impersonal. Not sarcastic. Not playful. Not corporate-robotic.

---

## 3. Hard rules — prohibited terms

These are **banned** in every user-facing string. `lint-copy.sh` (in F0+)
greps for them in `messages/**/*.json` and blocks the build.

### 3.1 The SaaS ban

**Never use these words or phrases in copy**:

- ❌ "SaaS"
- ❌ "multi-tenant", "multitenant", "multi-tenancy"
- ❌ "plataforma" (in the marketing sense, not the OS sense)
- ❌ "solución empresarial"
- ❌ "enterprise-grade"
- ❌ "soluciones en la nube" / "cloud-based"
- ❌ "disrupción", "disruptivo", "disruptive"
- ❌ "ecosistema"
- ❌ "next-gen" / "next-generation"
- ❌ "reimagine" / "reimagining"
- ❌ "game-changer" / "cambio de juego"
- ❌ "leverage" / "apalancar" (in the metaphorical tech sense)
- ❌ "synergy" / "sinergia"
- ❌ "empodera" / "empower" (overused, almost meaningless now)

**Why the ban**: CrediFlux is a tool for financial institutions in RD,
not a Silicon Valley pitch. Our buyers recognize these words as marketing
noise and trust the product less when they hear them. The founder
explicitly rejected this language when the plan was designed.

### 3.2 Terms preferred instead

| Ban this | Use this |
|---|---|
| "Nuestra plataforma SaaS" | "CrediFlux" — just the name |
| "Solución de gestión de préstamos" | "Sistema para gestionar préstamos" or "Herramienta de cobranza" |
| "Empower a tu equipo" | "Organiza a tu equipo" or "Dale visibilidad a tu equipo" |
| "Transformación digital" | "Llevar tu cartera al digital" or just "Usar CrediFlux" |
| "Multi-tenant" | "Para cada financiera" or "Por cada entidad" |
| "Reimagining collections" | "Cobranza que funciona" |
| "World-class" | (just cut it — your user will decide) |
| "24/7 availability" | "Disponible siempre" or "Accesible a toda hora" |
| "State of the art" | (cut or specific: "diseñado para préstamos dominicanos") |
| "Cutting edge" | (cut — if something is actually new, say what it does) |

### 3.3 Emoji rules

- ❌ **Never** in error messages.
- ❌ **Never** in dashboard navigation.
- ❌ **Never** in success toasts beyond a single `✓`.
- ✅ OK in empty states (one per state, contextual, not decorative).
- ✅ OK in WhatsApp templates to customers (they expect it in that channel).
- ✅ OK in blog posts / social if editorial tone calls for it.

The default is no emoji. If you want one, justify it in the PR.

---

## 4. Tone by context

### 4.1 Dashboard (gestor-facing)

**Terse, operational, numeric-forward.**

Patterns:

- Buttons: imperative verb, 1–3 words. "Crear préstamo", "Guardar",
  "Cobrar", "Enviar recordatorio". Never "Haz clic aquí para guardar".
- Labels: noun, no period. "Monto", "Fecha de vencimiento", "Cliente".
- Placeholders: hint at format. "ej: 001-1234567-8" for cédula, "0.00"
  for money, not "Type here".
- Success toasts: past tense verb + optional entity. "Préstamo creado.",
  "Pago registrado.", "Recordatorio enviado a Juan Pérez.". Max 8 words.
- Error toasts: what went wrong + what to do. "No se pudo conectar al
  servidor. Revisa tu conexión.", never "Error: undefined".
- Loading states: present continuous verb. "Guardando...",
  "Enviando...", "Validando cédula...". Not "Please wait".
- Empty states: acknowledge + nudge. "Aún no hay cobros registrados hoy.
  Cuando registres uno, aparecerá aquí." + primary action button.
- Confirmations (destructive): name the thing. "¿Eliminar el préstamo
  LN-2026-0042 de Juan Pérez?" not "Are you sure?".

### 4.2 Landing (prospect-facing)

**Claro, con personalidad, dominicano.** Slightly warmer than dashboard
but never chatty.

Patterns:

- Headlines: short, concrete benefit. "Cobra más, más rápido."
  "Gestiona tu cartera sin salir del sistema." Not clever metaphors.
- Subtitles: 1 sentence, explains the how. "CrediFlux organiza tus
  préstamos, cobros y recordatorios en un solo lugar, diseñado para
  financieras pequeñas y medianas en RD."
- CTAs: imperative + specific outcome. "Pedir una demo", "Ver precios",
  "Hablar con ventas". Never "Click here" or "Learn more".
- Feature cards: noun title + verb benefit. "Cobranza automatizada —
  Enviá recordatorios por WhatsApp en segundos."
- Testimonial: real names, real titles, real numbers if possible.
  Anonymous quotes are the weakest form of social proof; avoid if you
  can.
- Pricing: cifras claras, sin trucos. "RD$X/mes por sucursal". Never
  "Desde..." without saying what's "desde".
- FAQ: questions in the user's voice. "¿Puedo probarlo antes de pagar?"
  not "Pruebas gratuitas disponibles".

### 4.3 Customer-facing templates (WhatsApp / email / SMS to borrower)

**Breve, respetuoso, accionable.** The borrower doesn't know CrediFlux.
They're reading a message "from" the financiera.

Patterns:

- Greeting: first name. "Hola Juan,"
- Context: one line. "Le recordamos que su cuota del préstamo vence el
  15 de abril."
- Detail: numbers inline, clear. "Monto a pagar: RD$4,500."
- Channel: where to pay / confirm. "Puede pagar en nuestras oficinas o
  por transferencia a [cuenta]."
- Closing: warm but brief. "Gracias por su preferencia. — {business_name}"
- NO mention of "CrediFlux" — the tenant's business_name is the sender.

**Never** threaten. Never use ALL CAPS (except for "URGENTE" in one
critical case, and only if the tenant enabled urgent mode).

### 4.4 Legal / compliance

**Formal, complete, no ambiguity.** Privacy, terms, contracts.

- Use full legal names and dates, never abbreviated.
- Use the passive voice when the actor doesn't matter. ("La información
  se conserva por 5 años.")
- Cite the relevant RD law or DGII resolution when applicable.
- Don't try to be friendly here. The goal is clarity, not warmth.

---

## 5. Language and region

### 5.1 Spanish dialect

**Español neutro dominicano**. Understandable to any Latin American
Spanish speaker, but with RD-specific terms where they're more natural
and won't confuse:

- "RD$" as currency (not "DOP", not "$" alone on ambiguous pages)
- "colmado" is fine in blog posts / testimonials, avoid in dashboard UI
- "cédula" (not "DNI", not "documento")
- "préstamo" (not "crédito" as the generic — "crédito" is fine for
  "línea de crédito")
- "cobrador" / "gestor de cobranza" / "oficial de cobros"
- "mora" (not "atraso" in financial context)
- "cuota" (not "mensualidad")
- "vencimiento" / "vence"
- "desembolso" for disbursement
- "financiera" / "cooperativa" / "microfinanciera" for the institution

**Avoid**: "vos" (Argentine), "tío/tía" (Spanish from Spain), "checar"
(Mexican), "lana" for money (Mexican slang).

**Use "tú" not "usted"** in dashboard (operator to their own tool,
familiar). **Use "usted"** in customer-facing templates (respectful,
formal). **Use "tú"** in landing marketing (prospect, inviting).

### 5.2 English (when we add /en/)

**Professional US English**, not UK. Avoid British spellings
(colour → color, organise → organize).

When a DR-specific term has no good English equivalent, **keep the
Spanish term and gloss it inline**:
- "cédula (national ID)"
- "gestor de cobranza (collections officer)"
- "financiera (lending institution)"

Same voice attributes as Spanish. Same ban list applies — "SaaS" and
"enterprise-grade" are banned in English too.

### 5.3 Number formatting

Per RD convention:

- **Money**: `RD$4,500.00` — comma for thousands, period for decimals,
  always 2 decimals for currency display.
- **Percentages**: `12.5%` — period for decimals, `%` attached no space.
- **Dates**: `15 de abril de 2026` (long) or `15/04/2026` (short,
  day/month/year). Never `April 15` or ISO in UI.
- **Times**: `14:30` (24-hour) in dashboard for unambiguous ops. `2:30 PM`
  in customer-facing templates.
- **Phone**: `809-555-1234` for DR, `+1-809-555-1234` for international.
- **Cédula**: `001-1234567-8` (three groups separated by hyphens). The
  system stores without hyphens; format on display only.

---

## 6. Voice in structured UI elements

### 6.1 Form labels

- Noun, capitalized first word, no colon or period. "Monto del préstamo"
  not "monto:" or "Enter amount".
- If required, visual asterisk; don't write "(obligatorio)".
- Hint text below input for format, not above. "ej: 001-1234567-8" for cédula.

### 6.2 Error messages on inputs

- Specific, one sentence, tells the user the fix.
- ✅ "La cédula debe tener 11 dígitos."
- ✅ "No encontramos esta cédula en el padrón. Verifica y vuelve a intentar."
- ❌ "Cédula inválida"
- ❌ "Error en el campo"

### 6.3 Toasts

| Type | Length | Tone | Example |
|---|---|---|---|
| Success | ≤ 8 words | Matter-of-fact past tense | "Préstamo LN-2026-0042 creado." |
| Error | ≤ 15 words | Blame the system, not the user, if ambiguous | "No se pudo enviar el recordatorio. Revisa la conexión y vuelve a intentar." |
| Warning | ≤ 12 words | Direct, actionable | "La cédula del cliente no fue verificada en el padrón." |
| Info | ≤ 15 words | Neutral | "El pago se registrará en la cuenta del cliente en las próximas 24 horas." |

Auto-dismiss after: 4s success, 8s warning, never for error (requires dismiss).

### 6.4 Confirmation dialogs

Three parts:

1. **Title** — the action as a question with the entity named.
   "¿Eliminar el cliente Juan Pérez?"
2. **Body** — 1–2 sentences on consequences.
   "Esto borrará también sus 3 préstamos activos y el historial de
   pagos. No se puede deshacer."
3. **Buttons** — specific verb, not "Yes/No".
   Primary: "Eliminar" (destructive styling)
   Secondary: "Cancelar"

Never use the browser's native `confirm()`. Always a styled modal.

### 6.5 Empty states

See `DESIGN_SYSTEM.md` § 8 for visual. Voice-wise:

- Heading: warm acknowledgment, not "no data".
  ✅ "Aún no hay clientes en el sistema"
  ❌ "No data"
- Subtext: explain + nudge.
  "Agregar un cliente es el primer paso antes de otorgar préstamos.
  Puedes importarlos en lote o crear uno manualmente."
- Action button: the likely next step.

### 6.6 Loading states

- Present continuous + entity.
  ✅ "Guardando préstamo..."
  ❌ "Loading..."
- If it takes > 5s, update the text.
  "Guardando préstamo... esto está tardando más de lo normal."

### 6.7 Notification badges

Numeric only for counts (`"3"` on ReminderBell). Text optional.
No "New!" tags — newness is temporal, and what's new today is stale
tomorrow.

---

## 7. Do and don't — quick reference

| Do | Don't |
|---|---|
| "Guardado." | "¡Su información ha sido guardada con éxito!" |
| "Préstamo creado" | "Success!" |
| "¿Eliminar el cliente Juan Pérez?" | "Are you sure?" |
| "Cobra más, más rápido." | "Empowering financial transformation." |
| "Aún no hay préstamos hoy" | "No data available" |
| "Sistema para gestionar préstamos" | "Next-gen SaaS platform" |
| "Diseñado para RD" | "Solución enterprise-grade" |
| "CrediFlux" | "nuestra plataforma" |
| "Por cada sucursal" | "Per tenant" |
| Spanish in dashboard | Spanglish in dashboard |

---

## 8. Review checklist for new copy

Before merging any PR that changes user-facing strings, verify:

- [ ] No banned terms (§ 3.1)
- [ ] Dialect is español neutro RD (§ 5.1)
- [ ] Numbers and dates use RD conventions (§ 5.3)
- [ ] Buttons are imperative 1–3 words
- [ ] Errors tell the user the fix
- [ ] Empty states have warmth + a next step
- [ ] No emoji beyond the rules in § 3.3
- [ ] CTA says what will happen, not "Click here"
- [ ] The word "CrediFlux" appears in the marketing site, never in
      customer templates
- [ ] All strings extracted to `messages/es/*.json` (no hardcoded copy)

---

## 9. Changelog

- **2026-04-09** — v1 written as part of F0 of the v2.0 overhaul.
  SaaS ban locked. Dialect locked to RD neutro. Dashboard uses "tú",
  customer templates use "usted".
