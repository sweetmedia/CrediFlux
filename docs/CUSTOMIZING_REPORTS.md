# Customización de Reportes PDF

Este documento explica cómo customizar y crear reportes PDF en CrediFlux.

## Estructura del Sistema de Reportes

Los reportes PDF se encuentran en:
```
backend/apps/loans/reports.py
```

### Clase Base: LoanBalanceReport

Esta clase genera el reporte "Balance de Cuotas" y puede servir como plantilla para crear otros reportes.

## Cómo Customizar el Reporte Existente

### 1. Logo del Tenant

El logo del tenant se agrega automáticamente si está configurado:

```python
# El logo se obtiene del tenant actual
tenant = connection.tenant
if tenant and tenant.logo:
    pdf.drawImage(logo_path, x, y, width, height)
```

**Para agregar un logo:**
1. Ve a la configuración de tu tenant en el admin
2. Sube una imagen en el campo "Logo"
3. El logo aparecerá automáticamente en los reportes

### 2. Colores y Estilo

Puedes modificar colores, fuentes y estilos directamente en el código:

```python
# Cambiar tamaño de fuente
pdf.setFont("Helvetica-Bold", 14)  # Título más grande

# Cambiar colores (RGB)
pdf.setFillColorRGB(0.2, 0.4, 0.8)  # Azul personalizado

# Agregar líneas decorativas
pdf.setStrokeColorRGB(0, 0, 1)  # Azul
pdf.line(x1, y1, x2, y2)
```

### 3. Orientación de Página

El reporte actualmente usa orientación **Landscape** (horizontal):

```python
pdf = canvas.Canvas(self.buffer, pagesize=landscape(letter))
```

Para cambiar a Portrait (vertical):
```python
pdf = canvas.Canvas(self.buffer, pagesize=letter)
```

### 4. Formato de Números y Fechas

#### Números con formato de moneda:
```python
formatted = f"${amount:,.2f}"  # $100,000.00
```

#### Fechas en formato local:
```python
fecha = date_obj.strftime('%d/%m/%Y')  # 01/11/2025
```

#### Cédula con guiones:
```python
cedula_formateada = self._format_cedula("03103847012")  # 031-0384701-2
```

## Cómo Crear un Nuevo Reporte

### Paso 1: Crear la Clase del Reporte

Crea una nueva clase en `backend/apps/loans/reports.py`:

```python
class LoanSummaryReport:
    """Reporte resumido de préstamos"""

    def __init__(self, loan: Loan):
        self.loan = loan
        self.buffer = BytesIO()

    def generate(self):
        # Configurar página
        pdf = canvas.Canvas(self.buffer, pagesize=letter)
        width, height = letter

        # Agregar contenido
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(100, height - 100, "Resumen de Préstamo")

        # Agregar más contenido...

        # Guardar y retornar
        pdf.save()
        pdf_data = self.buffer.getvalue()
        self.buffer.close()
        return pdf_data
```

### Paso 2: Agregar el Endpoint en Views

En `backend/apps/loans/views.py`, agrega un nuevo action:

```python
@action(detail=True, methods=['get'])
def summary_report(self, request, pk=None):
    """Generar reporte resumido del préstamo"""
    from .reports import LoanSummaryReport

    loan = self.get_object()
    report = LoanSummaryReport(loan)
    pdf_data = report.generate()

    response = HttpResponse(pdf_data, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="resumen_{loan.loan_number}.pdf"'

    return response
```

### Paso 3: Agregar Función en el Frontend

En `frontend/lib/api/loans.ts`:

```typescript
async downloadSummaryReport(id: string): Promise<void> {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const token = localStorage.getItem('access_token');

  const response = await fetch(`${API_URL}/api/loans/${id}/summary_report/`, {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });

  if (!response.ok) {
    throw new Error('Error al descargar el reporte');
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `resumen_${id}.pdf`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
},
```

### Paso 4: Agregar Botón en la UI

En `frontend/app/loans/[id]/page.tsx`:

```typescript
<Button
  variant="outline"
  onClick={async () => {
    try {
      await loansAPI.downloadSummaryReport(loan.id);
    } catch (err) {
      setError('Error al descargar el reporte');
    }
  }}
>
  <Download className="mr-2 h-4 w-4" />
  Resumen PDF
</Button>
```

## Ejemplos de Customización Avanzada

### Agregar Tablas con ReportLab

```python
from reportlab.platypus import Table, TableStyle

# Crear datos de tabla
data = [
    ['Cuota', 'Fecha', 'Monto'],
    ['1', '01/11/2025', '$1,000.00'],
    ['2', '01/12/2025', '$1,000.00'],
]

# Crear tabla
table = Table(data, colWidths=[50, 100, 100])
table.setStyle(TableStyle([
    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
    ('FONTSIZE', (0, 0), (-1, 0), 10),
    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ('GRID', (0, 0), (-1, -1), 1, colors.black)
]))

# Dibujar en el PDF
table.wrapOn(pdf, width, height)
table.drawOn(pdf, x, y)
```

### Agregar Gráficos con ReportLab Graphics

```python
from reportlab.graphics.shapes import Drawing, Rect
from reportlab.graphics.charts.piecharts import Pie

# Crear gráfico de pie
drawing = Drawing(200, 200)
pie = Pie()
pie.x = 50
pie.y = 50
pie.width = 100
pie.height = 100
pie.data = [40, 30, 20, 10]
pie.labels = ['Capital', 'Interés', 'Mora', 'Otros']

drawing.add(pie)
drawing.drawOn(pdf, x, y)
```

### Agregar Marca de Agua

```python
# Guardar estado
pdf.saveState()

# Configurar transparencia y rotación
pdf.setFillAlpha(0.1)
pdf.rotate(45)

# Dibujar texto de marca de agua
pdf.setFont("Helvetica-Bold", 60)
pdf.drawString(100, 100, "CONFIDENCIAL")

# Restaurar estado
pdf.restoreState()
```

### Multi-página con Encabezado/Pie Consistente

```python
def draw_header(pdf, width, y_position):
    """Dibuja encabezado en cada página"""
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, y_position, "MI EMPRESA")
    pdf.drawRightString(width - 40, y_position, datetime.now().strftime('%d/%m/%Y'))
    return y_position - 30

def draw_footer(pdf, width, page_num):
    """Dibuja pie de página en cada página"""
    pdf.setFont("Helvetica", 8)
    pdf.drawCentredString(width/2, 30, f"Página {page_num}")

# En el loop principal
y_position = draw_header(pdf, width, height - 40)

# ... contenido ...

if y_position < 80:  # Necesita nueva página
    draw_footer(pdf, width, page_num)
    pdf.showPage()
    page_num += 1
    y_position = draw_header(pdf, width, height - 40)
```

## Tips y Mejores Prácticas

1. **Siempre usa try-except** para manejar errores al cargar imágenes o archivos
2. **Preserva aspect ratio** de imágenes para evitar distorsión
3. **Usa constantes** para colores y tamaños recurrentes
4. **Testea con diferentes cantidades de datos** (1 cuota vs 100 cuotas)
5. **Considera la orientación** (Portrait vs Landscape) según el contenido
6. **Usa fuentes estándar** (Helvetica, Times, Courier) para compatibilidad
7. **Agrega logging** para debug cuando algo falla

## Recursos Adicionales

- [ReportLab User Guide](https://www.reportlab.com/docs/reportlab-userguide.pdf)
- [ReportLab Graphics Guide](https://www.reportlab.com/docs/reportlab-graphics.pdf)
- [Python Color Names](https://matplotlib.org/stable/gallery/color/named_colors.html)

## Soporte

Para más información o ayuda, consulta la documentación oficial de ReportLab o contacta al equipo de desarrollo.
