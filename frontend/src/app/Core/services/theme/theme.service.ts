import { Injectable, signal, effect } from '@angular/core';

export type Theme = 'dark' | 'light';

@Injectable({
  providedIn: 'root',
})
export class ThemeService {
  private readonly STORAGE_KEY = 'swmm-theme';

  /** Current theme signal — default is dark */
  theme = signal<Theme>('dark');

  constructor() {
    // Apply the theme whenever the signal changes
    effect(() => {
      this.applyTheme(this.theme());
    });
  }

  /**
   * Call this once from MainLayout.ngOnInit to restore
   * the saved preference (or default to dark).
   */
  initTheme(): void {
    const saved = localStorage.getItem(this.STORAGE_KEY) as Theme | null;
    const initial: Theme = saved === 'light' ? 'light' : 'dark';
    this.theme.set(initial);
  }

  /** Toggle between dark and light */
  toggleTheme(): void {
    const next: Theme = this.theme() === 'dark' ? 'light' : 'dark';
    this.theme.set(next);
    localStorage.setItem(this.STORAGE_KEY, next);
  }

  private applyTheme(theme: Theme): void {
    document.documentElement.dataset['theme'] = theme;
  }
}
