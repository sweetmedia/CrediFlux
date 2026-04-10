'use client'

import { MapPin } from 'lucide-react'

import { cn } from '@/lib/utils'

interface MapMarker {
  lat: number
  lng: number
  label: string
  isPrimary?: boolean
}

interface CustomerMapProps {
  markers?: MapMarker[]
  className?: string
}

/**
 * Stub for the customer-location map component.
 *
 * F2 renders a placeholder. F3-quinquies will wire this up to the real
 * map component (likely mapcn over MapLibre GL + OSM tiles) once the
 * library URL is verified. The props interface here mirrors the final
 * contract so consumers can be written against it today.
 */
export function CustomerMap({ markers = [], className }: CustomerMapProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed bg-muted/30 p-8 text-center',
        className
      )}
    >
      <MapPin className="h-8 w-8 text-[var(--color-sage-400)]" strokeWidth={1.5} />
      <p className="text-sm font-medium text-foreground">Mapa de ubicaciones</p>
      <p className="text-xs text-muted-foreground">
        {markers.length > 0
          ? `${markers.length} ubicación${markers.length === 1 ? '' : 'es'} — se conecta en F3`
          : 'Componente pendiente — F3-quinquies'}
      </p>
    </div>
  )
}
