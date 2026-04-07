'use client';

import { useEffect, useRef, RefObject } from 'react';

type AnimationType = 'fadeIn' | 'fadeInUp' | 'fadeInDown' | 'fadeInLeft' | 'fadeInRight' | 'scaleIn' | 'slideIn';

interface AnimationOptions {
  duration?: number;
  delay?: number;
  ease?: string;
  stagger?: number;
}

const animationConfigs: Record<AnimationType, { from: object; to: object }> = {
  fadeIn: {
    from: { opacity: 0 },
    to: { opacity: 1 },
  },
  fadeInUp: {
    from: { opacity: 0, y: 30 },
    to: { opacity: 1, y: 0 },
  },
  fadeInDown: {
    from: { opacity: 0, y: -30 },
    to: { opacity: 1, y: 0 },
  },
  fadeInLeft: {
    from: { opacity: 0, x: -30 },
    to: { opacity: 1, x: 0 },
  },
  fadeInRight: {
    from: { opacity: 0, x: 30 },
    to: { opacity: 1, x: 0 },
  },
  scaleIn: {
    from: { opacity: 0, scale: 0.9 },
    to: { opacity: 1, scale: 1 },
  },
  slideIn: {
    from: { opacity: 0, x: 50 },
    to: { opacity: 1, x: 0 },
  },
};

/**
 * Hook for animating a single element on mount
 */
export function useGsapAnimation<T extends HTMLElement>(
  type: AnimationType = 'fadeInUp',
  options: AnimationOptions = {}
): RefObject<T> {
  const ref = useRef<T>(null);

  useEffect(() => {
    if (!ref.current) return;

    const config = animationConfigs[type];
    const { duration = 0.5, delay = 0, ease = 'power2.out' } = options;

    import('gsap').then(({ default: gsap }) => {
      gsap.fromTo(ref.current, config.from, {
        ...config.to,
        duration,
        delay,
        ease,
      });
    });
  }, [type, options.duration, options.delay, options.ease]);

  return ref;
}

/**
 * Hook for staggered animations of multiple elements
 */
export function useGsapStagger<T extends HTMLElement>(
  type: AnimationType = 'fadeInUp',
  options: AnimationOptions = {}
): RefObject<T> {
  const containerRef = useRef<T>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const config = animationConfigs[type];
    const { duration = 0.5, delay = 0, ease = 'power2.out', stagger = 0.1 } = options;

    const children = containerRef.current.children;
    if (children.length === 0) return;

    import('gsap').then(({ default: gsap }) => {
      gsap.fromTo(children, config.from, {
        ...config.to,
        duration,
        delay,
        ease,
        stagger,
      });
    });
  }, [type, options.duration, options.delay, options.ease, options.stagger]);

  return containerRef;
}

/**
 * Imperative animation function for custom use
 */
export const animate = {
  fadeIn: (element: HTMLElement | null, options: AnimationOptions = {}) => {
    if (!element) return;
    const { duration = 0.5, delay = 0, ease = 'power2.out' } = options;
    import('gsap').then(({ default: gsap }) => {
      gsap.fromTo(element, { opacity: 0 }, { opacity: 1, duration, delay, ease });
    });
  },

  fadeInUp: (element: HTMLElement | null, options: AnimationOptions = {}) => {
    if (!element) return;
    const { duration = 0.5, delay = 0, ease = 'power2.out' } = options;
    import('gsap').then(({ default: gsap }) => {
      gsap.fromTo(element, { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration, delay, ease });
    });
  },

  fadeOut: (element: HTMLElement | null, options: AnimationOptions = {}) => {
    if (!element) return;
    const { duration = 0.3, delay = 0, ease = 'power2.in' } = options;
    import('gsap').then(({ default: gsap }) => {
      gsap.to(element, { opacity: 0, duration, delay, ease });
    });
  },

  stagger: (elements: HTMLElement[] | NodeListOf<Element>, type: AnimationType = 'fadeInUp', options: AnimationOptions = {}) => {
    const config = animationConfigs[type];
    const { duration = 0.5, delay = 0, ease = 'power2.out', stagger = 0.1 } = options;
    import('gsap').then(({ default: gsap }) => {
      gsap.fromTo(elements, config.from, {
        ...config.to,
        duration,
        delay,
        ease,
        stagger,
      });
    });
  },
};
