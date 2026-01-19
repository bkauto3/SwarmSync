'use client';

import { CheckCircle, Clock, Star, TrendingUp } from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

interface AgentCardProps {
  id: string;
  name: string;
  description: string;
  avatar?: string;
  category: string;
  capabilities: string[];
  rating: number;
  reviewCount: number;
  pricePerRequest: number;
  certified: boolean;
  responseTime: number; // in seconds
  successRate: number; // 0-100
}

export function AgentCard({
  id,
  name,
  description,
  avatar,
  category,
  capabilities,
  rating,
  reviewCount,
  pricePerRequest,
  certified,
  responseTime,
  successRate,
}: AgentCardProps) {
  return (
    <Link href={`/agents/${id}`}>
      <Card className="group h-full overflow-hidden border-[var(--border-base)] bg-[var(--surface-raised)] transition-all hover:shadow-lg hover:border-white/20 cursor-pointer">
        {/* Header with avatar and category badge */}
          <div className="relative h-24 bg-gradient-to-r from-white/5 to-transparent p-4 flex items-start justify-between">
          {avatar && (
            <Image
              src={avatar}
              alt={name}
              width={48}
              height={48}
              className="h-12 w-12 rounded-full border-2 border-white shadow-md"
            />
          )}
          <Badge variant="default" className="text-xs">
            {category}
          </Badge>
        </div>

        {/* Content */}
        <div className="p-5 space-y-4">
          {/* Title and certification */}
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h3 className="font-display text-lg text-white line-clamp-1">{name}</h3>
              {certified && (
                <CheckCircle className="h-4 w-4 text-emerald-600 flex-shrink-0" />
              )}
            </div>
            <p className="text-sm text-[var(--text-muted)] line-clamp-2">{description}</p>
          </div>

          {/* Rating */}
          <div className="flex items-center gap-2 text-sm">
            <div className="flex items-center gap-1">
              {[...Array(5)].map((_, i) => (
                <Star
                  key={i}
                  className={`h-3.5 w-3.5 ${
                    i < Math.floor(rating) ? 'fill-slate-400 text-[var(--text-muted)]' : 'text-slate-600'
                  }`}
                />
              ))}
            </div>
            <span className="text-[var(--text-muted)]">
              {rating.toFixed(1)} ({reviewCount})
            </span>
          </div>

          {/* Metrics */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="rounded-lg bg-[var(--surface-raised)] p-2 space-y-1">
              <div className="flex items-center gap-1 text-[var(--text-muted)]">
                <TrendingUp className="h-3.5 w-3.5" />
                Success Rate
              </div>
              <p className="font-semibold text-white">{successRate}%</p>
            </div>
            <div className="rounded-lg bg-[var(--surface-raised)] p-2 space-y-1">
              <div className="flex items-center gap-1 text-[var(--text-muted)]">
                <Clock className="h-3.5 w-3.5" />
                Response
              </div>
              <p className="font-semibold text-white">{responseTime}s</p>
            </div>
          </div>

          {/* Capabilities */}
          {capabilities.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs text-[var(--text-muted)] uppercase tracking-wider">Capabilities</p>
              <div className="flex flex-wrap gap-1.5">
                {capabilities.slice(0, 3).map((cap) => (
                  <Badge
                    key={cap}
                    variant="outline"
                    className="text-xs font-normal px-2 py-0.5"
                  >
                    {cap}
                  </Badge>
                ))}
                {capabilities.length > 3 && (
                  <Badge variant="outline" className="text-xs font-normal px-2 py-0.5">
                    +{capabilities.length - 3} more
                  </Badge>
                )}
              </div>
            </div>
          )}

          {/* Footer with price and action */}
          <div className="pt-4 border-t border-[var(--border-base)] flex items-center justify-between">
            <div className="text-sm">
              <p className="text-xs text-[var(--text-muted)]">Starting at</p>
              <p className="font-display text-white">
                ${(pricePerRequest / 100).toFixed(2)}
              </p>
            </div>
            <Button
              asChild
              size="sm"
              variant="outline"
              className="text-slate-300 hover:text-white hover:bg-white/10"
              onClick={(e) => {
                e.preventDefault();
              }}
            >
              <span>View Details</span>
            </Button>
          </div>
        </div>
      </Card>
    </Link>
  );
}
