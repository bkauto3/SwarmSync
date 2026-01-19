'use client';

import { useEffect } from 'react';

/**
 * Lightweight scroll animation observer.
 * Adds 'animate-fade-in-up' class to elements with 'animate-on-scroll' class
 * when they enter the viewport.
 */
export function ScrollAnimationObserver() {
    useEffect(() => {
        // Check if IntersectionObserver is supported
        if (!('IntersectionObserver' in window)) return;

        const observer = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        // Add the animation class
                        entry.target.classList.add('animate-fade-in-up');
                        // Remove the initial opacity-0 class so it stays visible after animation
                        entry.target.classList.remove('opacity-0-on-scroll');
                        // Stop observing once animated
                        observer.unobserve(entry.target);
                    }
                });
            },
            {
                root: null, // viewport
                rootMargin: '0px',
                threshold: 0.1, // Trigger when 10% of the element is visible
            }
        );

        // Find all elements to animate
        const elements = document.querySelectorAll('.animate-on-scroll');
        elements.forEach((el) => {
            // Ensure initial state is hidden
            el.classList.add('opacity-0-on-scroll');
            observer.observe(el);
        });

        return () => {
            observer.disconnect();
        };
    }, []);

    return null; // This component renders nothing
}
