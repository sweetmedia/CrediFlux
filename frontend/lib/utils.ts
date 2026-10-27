import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Monto con su moneda; RD$ salvo que la financiera elija otra. */
export function formatCurrency(amount: number, currency: string = "DOP"): string {
  return new Intl.NumberFormat(currency === "DOP" ? "es-DO" : "en-US", {
    style: "currency",
    currency: currency,
  }).format(amount)
}

export function formatDate(date: string | Date): string {
  return new Date(date).toLocaleDateString("es-DO", {
    year: "numeric",
    month: "long",
    day: "numeric",
  })
}

export function formatDateTime(date: string | Date): string {
  return new Date(date).toLocaleString("es-DO", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}
