'use client';

import { useEffect, useRef, useState } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import gsap from 'gsap';

export function NavigationProgress() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const progressRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isNavigating, setIsNavigating] = useState(false);

  useEffect(() => {
    if (!progressRef.current || !containerRef.current) return;

    // Show and animate progress bar
    setIsNavigating(true);

    // Reset and show
    gsap.set(containerRef.current, { opacity: 1 });
    gsap.set(progressRef.current, { width: '0%' });

    // Animate to 90% quickly
    gsap.to(progressRef.current, {
      width: '90%',
      duration: 0.5,
      ease: 'power2.out',
    });

    // Complete the animation after a short delay
    const completeTimer = setTimeout(() => {
      gsap.to(progressRef.current, {
        width: '100%',
        duration: 0.2,
        ease: 'power1.in',
        onComplete: () => {
          // Fade out
          gsap.to(containerRef.current, {
            opacity: 0,
            duration: 0.3,
            delay: 0.1,
            onComplete: () => {
              setIsNavigating(false);
            },
          });
        },
      });
    }, 300);

    return () => clearTimeout(completeTimer);
  }, [pathname, searchParams]);

  return (
    <div
      ref={containerRef}
      className="fixed top-0 left-0 right-0 z-[9999] h-1 bg-transparent pointer-events-none"
      style={{ opacity: 0 }}
    >
      <div
        ref={progressRef}
        className="h-full bg-gradient-to-r from-blue-500 via-blue-600 to-indigo-600 shadow-lg shadow-blue-500/50"
        style={{ width: '0%' }}
      />
    </div>
  );
}
