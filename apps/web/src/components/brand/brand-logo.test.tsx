import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { BrandLogo } from './brand-logo';

describe('BrandLogo', () => {
    it('renders with the correct alt text', () => {
        render(<BrandLogo />);
        expect(screen.getByAltText('Swarm Sync logo')).toBeInTheDocument();
    });

    it('renders with custom alt text', () => {
        render(<BrandLogo alt="Custom Logo Alt" />);
        expect(screen.getByAltText('Custom Logo Alt')).toBeInTheDocument();
    });

    it('renders with the correct link destination', () => {
        render(<BrandLogo />);
        const link = screen.getByRole('link', { name: /swarm sync homepage/i });
        expect(link).toHaveAttribute('href', '/');
    });

    it('renders with custom link destination', () => {
        render(<BrandLogo href="/custom-path" />);
        const link = screen.getByRole('link', { name: /swarm sync homepage/i });
        expect(link).toHaveAttribute('href', '/custom-path');
    });

    it('contains the logo image', () => {
        render(<BrandLogo />);
        const image = screen.getByAltText('Swarm Sync logo');
        expect(image).toBeInTheDocument();
        expect(image.tagName).toBe('IMG');
    });
});
