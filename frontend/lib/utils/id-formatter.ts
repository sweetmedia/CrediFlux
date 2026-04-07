/**
 * Formateadores automáticos para identificaciones dominicanas
 * Añaden guiones mientras el usuario escribe
 */

/**
 * Formatear Cédula: XXX-XXXXXXX-X
 */
export function formatCedula(value: string): string {
  // Remover todo excepto números
  const cleaned = value.replace(/\D/g, '');

  // Limitar a 11 dígitos
  const limited = cleaned.slice(0, 11);

  // Aplicar formato
  if (limited.length <= 3) {
    return limited;
  } else if (limited.length <= 10) {
    return `${limited.slice(0, 3)}-${limited.slice(3)}`;
  } else {
    return `${limited.slice(0, 3)}-${limited.slice(3, 10)}-${limited.slice(10)}`;
  }
}

/**
 * Formatear RNC: X-XX-XXXXX-X
 */
export function formatRNC(value: string): string {
  // Remover todo excepto números
  const cleaned = value.replace(/\D/g, '');

  // Limitar a 9 dígitos
  const limited = cleaned.slice(0, 9);

  // Aplicar formato
  if (limited.length <= 1) {
    return limited;
  } else if (limited.length <= 3) {
    return `${limited.slice(0, 1)}-${limited.slice(1)}`;
  } else if (limited.length <= 8) {
    return `${limited.slice(0, 1)}-${limited.slice(1, 3)}-${limited.slice(3)}`;
  } else {
    return `${limited.slice(0, 1)}-${limited.slice(1, 3)}-${limited.slice(3, 8)}-${limited.slice(8)}`;
  }
}

/**
 * Formatear NSS: XXX-XXXXXX-X
 */
export function formatNSS(value: string): string {
  // Remover todo excepto números
  const cleaned = value.replace(/\D/g, '');

  // Limitar a 11 dígitos (puede ser 10 u 11)
  const limited = cleaned.slice(0, 11);

  // Aplicar formato
  if (limited.length <= 3) {
    return limited;
  } else if (limited.length <= 9) {
    return `${limited.slice(0, 3)}-${limited.slice(3)}`;
  } else {
    return `${limited.slice(0, 3)}-${limited.slice(3, 9)}-${limited.slice(9)}`;
  }
}

/**
 * Formatear según tipo de ID
 */
export function formatIDNumber(
  value: string,
  type: 'cedula' | 'rnc' | 'nss' | 'ncf' | 'passport' | 'driver_license'
): string {
  switch (type) {
    case 'cedula':
      return formatCedula(value);
    case 'rnc':
      return formatRNC(value);
    case 'nss':
      return formatNSS(value);
    case 'ncf':
      // NCF se formatea en mayúsculas, sin modificar estructura
      return value.toUpperCase().slice(0, 13); // E + 2 dígitos + 8 dígitos
    case 'passport':
    case 'driver_license':
      // Estos no tienen formato específico
      return value;
    default:
      return value;
  }
}

/**
 * Limpiar formato (remover guiones) para enviar al backend
 */
export function cleanIDNumber(value: string): string {
  return value.replace(/[-\s]/g, '');
}

/**
 * Obtener placeholder según tipo de ID
 */
export function getIDPlaceholder(
  type: 'cedula' | 'rnc' | 'nss' | 'ncf' | 'passport' | 'driver_license'
): string {
  switch (type) {
    case 'cedula':
      return '000-0000000-0';
    case 'rnc':
      return '0-00-00000-0';
    case 'nss':
      return '000-000000-0';
    case 'ncf':
      return 'E310000000001';
    case 'passport':
      return 'AB123456';
    case 'driver_license':
      return '00000000';
    default:
      return '';
  }
}

/**
 * Obtener máxima longitud del input según tipo
 */
export function getIDMaxLength(
  type: 'cedula' | 'rnc' | 'nss' | 'ncf' | 'passport' | 'driver_license'
): number {
  switch (type) {
    case 'cedula':
      return 13; // 11 dígitos + 2 guiones
    case 'rnc':
      return 11; // 9 dígitos + 3 guiones (pero solo usamos 2 según el formato)
    case 'nss':
      return 12; // 10-11 dígitos + 2 guiones
    case 'ncf':
      return 13; // Letra + 10 dígitos
    case 'passport':
      return 20;
    case 'driver_license':
      return 12;
    default:
      return 50;
  }
}
