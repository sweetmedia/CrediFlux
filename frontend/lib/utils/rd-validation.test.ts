import { describe, expect, it } from "vitest";
import {
  formatDominicanID,
  validateCedula,
  validateDominicanID,
  validateNCF,
  validateNSS,
  validateRNC,
} from "./rd-validation";

describe("validateCedula", () => {
  it("acepta una cédula que pasa Luhn y la formatea", () => {
    expect(validateCedula("402-1234567-8")).toMatchObject({
      valid: true,
      warning: false,
      formatted: "402-1234567-8",
    });
  });

  it("deja pasar con advertencia una cédula que no cumple Luhn", () => {
    // La JCE emitió cédulas válidas que no cumplen Luhn: no se bloquean.
    expect(validateCedula("40212345670")).toMatchObject({ valid: true, warning: true });
  });

  it.each([
    ["4021234567", "exactamente 11 dígitos"],
    ["402-ABC4567-8", "solo números"],
  ])("rechaza %s", (cedula, mensaje) => {
    const r = validateCedula(cedula);
    expect(r.valid).toBe(false);
    expect(r.message).toContain(mensaje);
  });
});

describe("validateRNC", () => {
  it("acepta un RNC de 9 dígitos y lo formatea X-XX-XXXXX-X", () => {
    expect(validateRNC("101000016")).toMatchObject({
      valid: true,
      warning: false,
      formatted: "1-01-00001-6",
    });
  });

  it("rechaza longitudes distintas de 9", () => {
    expect(validateRNC("1010000").valid).toBe(false);
  });
});

describe("validateNCF", () => {
  it("acepta un NCF serie B de 11 caracteres", () => {
    expect(validateNCF("b0100000001")).toEqual({
      valid: true,
      message: "NCF válido",
      formatted: "B01-00000001",
    });
  });

  it("rechaza un tipo de comprobante inexistente", () => {
    expect(validateNCF("B9900000001").valid).toBe(false);
  });

  // BUG CONOCIDO: un e-NCF es E + 2 dígitos de tipo + 10 de secuencia (13
  // caracteres), pero la regex exige letra + 10 dígitos. El propio mensaje de
  // error usa E310000000001 como ejemplo y lo rechaza. Cuando se corrija,
  // `it.fails` empezará a fallar: cámbialo a `it`.
  it.fails("acepta un e-NCF de 13 caracteres (E31 + 10 dígitos)", () => {
    expect(validateNCF("E310000000001").valid).toBe(true);
  });
});

describe("validateNSS", () => {
  it.each([
    ["0011234567", "001-123456-7"],
    ["00112345678", "001-1234567-8"],
  ])("formatea %s como %s", (nss, formatted) => {
    expect(validateNSS(nss)).toMatchObject({ valid: true, formatted });
  });
});

describe("validateDominicanID / formatDominicanID", () => {
  it("exige un valor", () => {
    expect(validateDominicanID("  ", "cedula").valid).toBe(false);
  });

  it("pasaporte: mínimo 6 caracteres, en mayúsculas", () => {
    expect(validateDominicanID("ab12", "passport").valid).toBe(false);
    expect(formatDominicanID("ab1234", "passport")).toBe("AB1234");
  });

  it("devuelve el valor original cuando no puede formatear", () => {
    expect(formatDominicanID("xyz", "rnc")).toBe("xyz");
  });
});
