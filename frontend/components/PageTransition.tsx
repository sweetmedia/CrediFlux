'use client';

import { useEffect, useRef, useState } from 'react';
import { usePathname } from 'next/navigation';

interface PageTransitionProps {
  children: React.ReactNode;
}

// Simpler version that just animates on pathname change
export function SimplePageTransition({ children }: PageTransitionProps) {
  const pathname = usePathname();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Dynamically import GSAP
    import('gsap').then(({ default: gsap }) => {
      gsap.fromTo(
        containerRef.current,
        { opacity: 0, y: 15 },
        { opacity: 1, y: 0, duration: 0.35, ease: 'power2.out' }
      );
    });
  }, [pathname]);

  return (
    <div ref={containerRef}>
      {children}
    </div>
  );
}

// Fade transition
export function FadeTransition({ children }: PageTransitionProps) {
  const pathname = usePathname();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    import('gsap').then(({ default: gsap }) => {
      gsap.fromTo(
        containerRef.current,
        { opacity: 0 },
        { opacity: 1, duration: 0.3, ease: 'power1.out' }
      );
    });
  }, [pathname]);

  return (
    <div ref={containerRef}>
      {children}
    </div>
  );
}

// Slide transition
export function SlideTransition({ children }: PageTransitionProps) {
  const pathname = usePathname();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    import('gsap').then(({ default: gsap }) => {
      gsap.fromTo(
        containerRef.current,
        { opacity: 0, x: 30 },
        { opacity: 1, x: 0, duration: 0.4, ease: 'power3.out' }
      );
    });
  }, [pathname]);

  return (
    <div ref={containerRef}>
      {children}
    </div>
  );
}

// Scale transition
export function ScaleTransition({ children }: PageTransitionProps) {
  const pathname = usePathname();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    import('gsap').then(({ default: gsap }) => {
      gsap.fromTo(
        containerRef.current,
        { opacity: 0, scale: 0.95 },
        { opacity: 1, scale: 1, duration: 0.35, ease: 'power2.out' }
      );
    });
  }, [pathname]);

  return (
    <div ref={containerRef}>
      {children}
    </div>
  );
}
