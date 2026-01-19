'use client';

import { useEffect, useState } from 'react';

export function BackgroundToggle() {
  const [hideBackground, setHideBackground] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('hideBackground') === 'true';
      setHideBackground(stored);
      if (stored) {
        document.documentElement.classList.add('no-background');
      }
    }
  }, []);

  const handleToggle = (checked: boolean) => {
    setHideBackground(checked);
    localStorage.setItem('hideBackground', checked.toString());
    if (checked) {
      document.documentElement.classList.add('no-background');
    } else {
      document.documentElement.classList.remove('no-background');
    }
  };

  return (
    <div className="flex items-center justify-between">
      <div>
        <label htmlFor="hideBackground" className="text-sm font-medium text-[var(--text-primary)]" font-ui>
          Remove Background
        </label>
        <p className="text-xs text-[var(--text-muted)] mt-1" font-ui>
          Hide the starfield and network background for a cleaner console view
        </p>
      </div>
      <label className="relative inline-flex items-center cursor-pointer">
        <input
          type="checkbox"
          id="hideBackground"
          checked={hideBackground}
          onChange={(e) => handleToggle(e.target.checked)}
          className="sr-only peer"
        />
        <div className="w-11 h-6 bg-[var(--surface-raised)] peer-focus:outline-none peer-focus:ring-2 peer-focus:ring-[var(--shadow-focus)] rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-[var(--accent-primary)]"></div>
      </label>
    </div>
  );
}

