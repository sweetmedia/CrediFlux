/**
 * `<Image>` liviano: un `<img>` con la API que usaba la app con `next/image`
 * (src, alt, width, height, priority). Vite sirve `public/` tal cual, sin
 * optimizador de imágenes.
 */
import { forwardRef, type ImgHTMLAttributes } from 'react';

export interface ImageProps extends Omit<ImgHTMLAttributes<HTMLImageElement>, 'src'> {
  src: string;
  alt: string;
  /** Carga inmediata y con prioridad alta (logos above-the-fold). */
  priority?: boolean;
}

const Image = forwardRef<HTMLImageElement, ImageProps>(function Image(
  { priority, loading, decoding, ...rest },
  ref
) {
  return (
    <img
      ref={ref}
      loading={loading ?? (priority ? 'eager' : 'lazy')}
      decoding={decoding ?? 'async'}
      fetchPriority={priority ? 'high' : undefined}
      {...rest}
    />
  );
});

export default Image;
