'use client';

import { useEffect, useRef, useState } from 'react';
import { usePathname } from 'next/navigation';
import gsap from 'gsap';

interface PageTransitionProps {
  children: React.ReactNode;
}

export function PageTransition({ children }: PageTransitionProps) {
  const pathname = usePathname();
  const containerRef = useRef<HTMLDivElement>(null);
  const [displayChildren, setDisplayChildren] = useState(children);
  const [isAnimating, setIsAnimating] = useState(false);

  useEffect(() => {
    // Skip animation on initial mount
    if (!containerRef.current) return;

    // If children changed (new page), animate
    if (children !== displayChildren && !isAnimating) {
      setIsAnimating(true);

      // Exit animation
      gsap.to(containerRef.current, {
        opacity: 0,
        y: 20,
        duration: 0.2,
        ease: 'power2.in',
        onComplete: () => {
          // Update to new content
          setDisplayChildren(children);

          // Enter animation
          gsap.fromTo(
            containerRef.current,
            { opacity: 0, y: -20 },
            {
              opacity: 1,
              y: 0,
              duration: 0.3,
              ease: 'power2.out',
              onComplete: () => {
                setIsAnimating(false);
              },
            }
          );
        },
      });
    }
  }, [children, displayChildren, isAnimating]);

  // Initial mount animation
  useEffect(() => {
    if (containerRef.current) {
      gsap.fromTo(
        containerRef.current,
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.4, ease: 'power2.out' }
      );
    }
  }, []);

  return (
    <div ref={containerRef} className="page-transition-container">
      {displayChildren}
    </div>
  );
}

// Simpler version that just animates on pathname change
export function SimplePageTransition({ children }: PageTransitionProps) {
  const pathname = usePathname();
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // Animate on every pathname change
    gsap.fromTo(
      containerRef.current,
      { opacity: 0, y: 15 },
      { opacity: 1, y: 0, duration: 0.35, ease: 'power2.out' }
    );
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

    gsap.fromTo(
      containerRef.current,
      { opacity: 0 },
      { opacity: 1, duration: 0.3, ease: 'power1.out' }
    );
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

    gsap.fromTo(
      containerRef.current,
      { opacity: 0, x: 30 },
      { opacity: 1, x: 0, duration: 0.4, ease: 'power3.out' }
    );
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

    gsap.fromTo(
      containerRef.current,
      { opacity: 0, scale: 0.95 },
      { opacity: 1, scale: 1, duration: 0.35, ease: 'power2.out' }
    );
  }, [pathname]);

  return (
    <div ref={containerRef}>
      {children}
    </div>
  );
}
