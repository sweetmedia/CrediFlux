/**
 * Utilidades de validación para identificaciones de la República Dominicana
 * Incluye: Cédula, RNC, NCF, NSS
 */

/**
 * Algoritmo de Luhn (Mod 10)
 * Usado para validar cédulas y RNC
 */
function luhnCheck(value: string): boolean {
  if (!value || !/^\d+$/.test(value)) {
    return false;
  }

  let sum = 0;
  let isEven = false;

  // Recorrer de derecha a izquierda
  for (let i = value.length - 1; i >= 0; i--) {
    let digit = parseInt(value[i], 10);

    if (isEven) {
      digit *= 2;
      if (digit > 9) {
        digit -= 9;
      }
    }

    sum += digit;
    isEven = !isEven;
  }

  return sum % 10 === 0;
}

/**
 * Validar Cédula Dominicana
 * Formato: 11 dígitos
 * Usa algoritmo de Luhn
 */
export function validateCedula(cedula: string): {
  valid: boolean;
  warning?: boolean;
  message: string;
  formatted?: string;
} {
  // Limpiar espacios y guiones
  const cleaned = cedula.replace(/[\s-]/g, '');

  // Validar solo números
  if (!/^\d+$/.test(cleaned)) {
    return {
      valid: false,
      message: 'La cédula debe contener solo números',
    };
  }

  // Validar longitud
  if (cleaned.length !== 11) {
    return {
      valid: false,
      message: 'La cédula debe tener exactamente 11 dígitos',
    };
  }

  // Validar con algoritmo de Luhn
  const passesLuhn = luhnCheck(cleaned);

  // Formatear: XXX-XXXXXXX-X
  const formatted = `${cleaned.slice(0, 3)}-${cleaned.slice(3, 10)}-${cleaned.slice(10)}`;

  if (!passesLuhn) {
    // Nota: Algunas cédulas válidas emitidas por la JCE no cumplen con el algoritmo de Luhn
    // No bloqueamos, solo advertimos
    return {
      valid: true, // Permitir continuar
      warning: true, // Mostrar como advertencia
      message: '⚠️ Formato no estándar. Se verificará con DGII.',
      formatted,
    };
  }

  return {
    valid: true,
    warning: false,
    message: '✓ Formato válido',
    formatted,
  };
}

/**
 * Validar RNC (Registro Nacional de Contribuyentes)
 * Formato: 9 dígitos
 * Usa algoritmo de Luhn
 */
export function validateRNC(rnc: string): {
  valid: boolean;
  warning?: boolean;
  message: string;
  formatted?: string;
} {
  // Limpiar espacios y guiones
  const cleaned = rnc.replace(/[\s-]/g, '');

  // Validar solo números
  if (!/^\d+$/.test(cleaned)) {
    return {
      valid: false,
      message: 'El RNC debe contener solo números',
    };
  }

  // Validar longitud (9 dígitos)
  if (cleaned.length !== 9) {
    return {
      valid: false,
      message: 'El RNC debe tener exactamente 9 dígitos',
    };
  }

  // Validar con algoritmo de Luhn
  const passesLuhn = luhnCheck(cleaned);

  // Formatear: X-XX-XXXXX-X
  const formatted = `${cleaned.slice(0, 1)}-${cleaned.slice(1, 3)}-${cleaned.slice(3, 8)}-${cleaned.slice(8)}`;

  if (!passesLuhn) {
    // Nota: Algunos RNC válidos emitidos por la DGII no cumplen con el algoritmo de Luhn
    // No bloqueamos, solo advertimos
    return {
      valid: true, // Permitir continuar
      warning: true, // Mostrar como advertencia
      message: '⚠️ Formato no estándar. Se verificará con DGII.',
      formatted,
    };
  }

  return {
    valid: true,
    warning: false,
    message: '✓ Formato válido',
    formatted,
  };
}

/**
 * Validar NCF (Número de Comprobante Fiscal)
 * Formato: E + 2 dígitos (tipo) + 8 dígitos (secuencia)
 * Ejemplo: E310000000001, B0100000001
 */
export function validateNCF(ncf: string): {
  valid: boolean;
  message: string;
  formatted?: string;
} {
  // Limpiar espacios
  const cleaned = ncf.replace(/\s/g, '').toUpperCase();

  // Validar formato básico
  if (!/^[A-Z]\d{10}$/.test(cleaned)) {
    return {
      valid: false,
      message: 'NCF debe tener formato: Letra + 10 dígitos (ej: E310000000001)',
    };
  }

  // Extraer tipo y secuencia
  const letter = cleaned[0];
  const typeCode = cleaned.slice(1, 3);
  const sequence = cleaned.slice(3);

  // Tipos de NCF válidos según DGII
  const validTypes = [
    '01', // Facturas de Crédito Fiscal
    '02', // Facturas de Consumo
    '03', // Notas de Débito
    '04', // Notas de Crédito
    '11', // Proveedores Informales
    '12', // Registro Único de Ingresos
    '13', // Gastos Menores
    '14', // Regímenes Especiales
    '15', // Gubernamentales
    '31', // Facturas de Crédito Fiscal (e-CF)
    '32', // Facturas de Consumo (e-FC)
    '33', // Notas de Débito (e-ND)
    '34', // Notas de Crédito (e-NC)
    '41', // Compras
    '43', // Gastos Menores (e-GM)
    '44', // Regímenes Especiales (e-RE)
    '45', // Gubernamentales (e-GUB)
    '46', // Comprobante de Exportación
    '47', // Comprobante para Pagos al Exterior
  ];

  if (!validTypes.includes(typeCode)) {
    return {
      valid: false,
      message: `Tipo de NCF '${typeCode}' no es válido`,
    };
  }

  // Validar letra inicial (E o B típicamente)
  const validLetters = ['A', 'B', 'E'];
  if (!validLetters.includes(letter)) {
    return {
      valid: false,
      message: `NCF debe iniciar con A, B o E. Letra '${letter}' no es válida`,
    };
  }

  // Formatear: E31-00000001
  const formatted = `${letter}${typeCode}-${sequence}`;

  return {
    valid: true,
    message: 'NCF válido',
    formatted,
  };
}

/**
 * Validar NSS (Número de Seguridad Social)
 * Formato dominicano: XXX-XXXXXX-X (10 dígitos)
 */
export function validateNSS(nss: string): {
  valid: boolean;
  message: string;
  formatted?: string;
} {
  // Limpiar espacios y guiones
  const cleaned = nss.replace(/[\s-]/g, '');

  // Validar solo números
  if (!/^\d+$/.test(cleaned)) {
    return {
      valid: false,
      message: 'El NSS debe contener solo números',
    };
  }

  // Validar longitud
  if (cleaned.length !== 10 && cleaned.length !== 11) {
    return {
      valid: false,
      message: 'El NSS debe tener 10 u 11 dígitos',
    };
  }

  // Formatear: XXX-XXXXXX-X
  let formatted: string;
  if (cleaned.length === 10) {
    formatted = `${cleaned.slice(0, 3)}-${cleaned.slice(3, 9)}-${cleaned.slice(9)}`;
  } else {
    formatted = `${cleaned.slice(0, 3)}-${cleaned.slice(3, 10)}-${cleaned.slice(10)}`;
  }

  return {
    valid: true,
    message: 'NSS válido',
    formatted,
  };
}

/**
 * Validar cualquier tipo de identificación dominicana
 */
export function validateDominicanID(
  value: string,
  type: 'cedula' | 'rnc' | 'ncf' | 'nss' | 'passport' | 'driver_license'
): {
  valid: boolean;
  warning?: boolean;
  message: string;
  formatted?: string;
} {
  if (!value || value.trim() === '') {
    return {
      valid: false,
      message: 'El número de identificación es requerido',
    };
  }

  switch (type) {
    case 'cedula':
      return validateCedula(value);
    case 'rnc':
      return validateRNC(value);
    case 'ncf':
      return validateNCF(value);
    case 'nss':
      return validateNSS(value);
    case 'passport':
      // Pasaporte no tiene formato específico, solo validar longitud mínima
      if (value.length < 6) {
        return {
          valid: false,
          message: 'El pasaporte debe tener al menos 6 caracteres',
        };
      }
      return {
        valid: true,
        message: 'Pasaporte válido',
        formatted: value.toUpperCase(),
      };
    case 'driver_license':
      // Licencia de conducir dominicana tiene formato específico
      const cleanedLicense = value.replace(/[\s-]/g, '');
      if (!/^\d{8,12}$/.test(cleanedLicense)) {
        return {
          valid: false,
          message: 'La licencia debe tener entre 8 y 12 dígitos',
        };
      }
      return {
        valid: true,
        message: 'Licencia válida',
        formatted: cleanedLicense,
      };
    default:
      return {
        valid: false,
        message: 'Tipo de identificación no reconocido',
      };
  }
}

/**
 * Formatear número de identificación según tipo
 */
export function formatDominicanID(
  value: string,
  type: 'cedula' | 'rnc' | 'ncf' | 'nss' | 'passport' | 'driver_license'
): string {
  const result = validateDominicanID(value, type);
  return result.formatted || value;
}
