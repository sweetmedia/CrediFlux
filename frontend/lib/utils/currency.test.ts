import { describe, expect, it } from "vitest";
import { formatCurrency, formatMoney } from "./currency";

describe("formatMoney", () => {
  it("formatea con separadores es-DO y 2 decimales", () => {
    expect(formatMoney(1234.5, "RD$")).toBe("RD$1,234.50");
  });

  it("acepta los strings numéricos que devuelve la API", () => {
    expect(formatMoney("1500", "RD$")).toBe("RD$1,500.00");
  });

  it.each([null, undefined, "no-es-numero"])("trata %s como 0", (valor) => {
    expect(formatMoney(valor, "RD$")).toBe("RD$0.00");
  });

  it("respeta los decimales pedidos", () => {
    expect(formatMoney(10, "$", 0)).toBe("$10");
  });

  it("formatCurrency (deprecado) delega en formatMoney", () => {
    expect(formatCurrency(1, "US$")).toBe(formatMoney(1, "US$"));
  });
});
