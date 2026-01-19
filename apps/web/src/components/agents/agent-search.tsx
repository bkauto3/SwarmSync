'use client';

import { Search, X } from 'lucide-react';
import { ChangeEvent, useState, useRef, useEffect } from 'react';

import { Input } from '@/components/ui/input';

interface AgentSearchProps {
  value: string;
  onChange: (next: string) => void;
  placeholder?: string;
  suggestions?: string[];
  onSearch?: (query: string) => void;
}

export function AgentSearch({ value, onChange, placeholder = 'Search agents, workflows, or tags', suggestions = [], onSearch }: AgentSearchProps) {
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [filteredSuggestions, setFilteredSuggestions] = useState<string[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.value;
    onChange(newValue);

    if (onSearch && newValue.length > 2) {
      // Debounce search
      const timer = setTimeout(() => {
        onSearch(newValue);
      }, 300);
      return () => clearTimeout(timer);
    }

    if (newValue.length > 0 && suggestions.length > 0) {
      const filtered = suggestions.filter((suggestion) =>
        suggestion.toLowerCase().includes(newValue.toLowerCase())
      );
      setFilteredSuggestions(filtered.slice(0, 5));
      setShowSuggestions(filtered.length > 0);
    } else {
      setShowSuggestions(false);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    onChange(suggestion);
    setShowSuggestions(false);
    inputRef.current?.focus();
  };

  const handleClear = () => {
    onChange('');
    setShowSuggestions(false);
    inputRef.current?.focus();
  };

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative w-full max-w-2xl">
      <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
      <Input
        ref={inputRef}
        value={value}
        onChange={handleChange}
        onFocus={() => {
          if (value.length > 0 && filteredSuggestions.length > 0) {
            setShowSuggestions(true);
          }
        }}
        placeholder={placeholder}
        className="pl-11 pr-10 focus:ring-2 focus:ring-brass focus:ring-offset-2"
        type="search"
        aria-label="Search agents, workflows, or tags"
        aria-autocomplete="list"
        aria-expanded={showSuggestions}
      />
      {value && (
        <button
          type="button"
          onClick={handleClear}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
          aria-label="Clear search"
        >
          <X className="h-4 w-4" />
        </button>
      )}
      {showSuggestions && filteredSuggestions.length > 0 && (
        <div
          ref={suggestionsRef}
          className="absolute z-50 mt-1 w-full rounded-lg border border-white/10 bg-black shadow-lg"
          role="listbox"
        >
          {filteredSuggestions.map((suggestion, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSuggestionClick(suggestion)}
              className="w-full px-4 py-2 text-left text-sm text-[var(--text-secondary)] hover:bg-white/5 transition-colors"
              role="option"
            >
              <span dangerouslySetInnerHTML={{
                __html: suggestion.replace(
                  new RegExp(`(${value})`, 'gi'),
                  '<mark class="bg-yellow-400/30 text-yellow-200">$1</mark>'
                )
              }} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
