import { useLayoutEffect, useRef } from 'react';
import { usePathname } from '@/lib/navigation';
import gsap from 'gsap';

interface PageTransitionProps {
  children: React.ReactNode;
}

// Route change entrance. Navigation happens dozens of times a day, so it stays
// short and subtle. clearProps removes the inline transform afterwards: a
// leftover transform turns this wrapper into the containing block for every
// position:fixed descendant (modals would anchor to the page, not the viewport).
export function SimplePageTransition({ children }: PageTransitionProps) {
  const pathname = usePathname();
  const containerRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const mm = gsap.matchMedia();
    mm.add(
      {
        motion: '(prefers-reduced-motion: no-preference)',
        reduce: '(prefers-reduced-motion: reduce)',
      },
      (ctx) => {
        if (ctx.conditions?.reduce) {
          gsap.fromTo(el, { opacity: 0 }, { opacity: 1, duration: 0.15, ease: 'none', clearProps: 'opacity' });
        } else {
          gsap.fromTo(
            el,
            { opacity: 0, y: 6 },
            { opacity: 1, y: 0, duration: 0.2, ease: 'power3.out', clearProps: 'opacity,transform' }
          );
        }
      }
    );
    return () => mm.revert();
  }, [pathname]);

  return <div ref={containerRef}>{children}</div>;
}
