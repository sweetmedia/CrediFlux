"""
Core models — shared across all tenants (public schema).
"""
from django.db import models


class PadronJCE(models.Model):
    """
    Padrón electoral de la JCE (Junta Central Electoral).
    ~7.9 millones de ciudadanos dominicanos.
    Tabla en schema public, compartida entre todos los tenants.
    """
    cedula = models.CharField(max_length=15, unique=True, db_index=True)
    nombres = models.CharField(max_length=150)
    apellido1 = models.CharField(max_length=100)
    apellido2 = models.CharField(max_length=100, blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)

    class Meta:
        db_table = 'padron_jce'
        managed = False  # Table already exists, don't create via migrations
        verbose_name = 'Registro Padrón JCE'
        verbose_name_plural = 'Padrón JCE'

    def __str__(self):
        return f'{self.cedula} - {self.nombres} {self.apellido1}'

    @property
    def nombre_completo(self):
        parts = [self.nombres, self.apellido1]
        if self.apellido2:
            parts.append(self.apellido2)
        return ' '.join(parts)

    @property
    def cedula_formateada(self):
        """Formato: XXX-XXXXXXX-X"""
        c = self.cedula.replace('-', '').strip()
        if len(c) == 11:
            return f'{c[:3]}-{c[3:10]}-{c[10]}'
        return c
