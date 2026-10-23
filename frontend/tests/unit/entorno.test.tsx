import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { cn } from "@/lib/utils";

// Prueba de humo del entorno: jsdom + Testing Library + alias `@/`.
describe("entorno de pruebas", () => {
  it("renderiza componentes React en jsdom", () => {
    const activo = false as boolean;
    const { getByText } = render(<span className={cn("a", activo && "b", "c")}>hola</span>);
    expect(getByText("hola")).toBeInTheDocument();
    expect(getByText("hola")).toHaveClass("a", "c");
  });
});
