'use client';

import { Search, Filter, FlaskConical } from 'lucide-react';
import { useState, useEffect } from 'react';

import { TestWizardModal } from '@/components/testing/test-wizard-modal';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { testingApi, agentsApi, type TestSuite, type Agent, type IndividualTest } from '@/lib/api';

export default function TestLibraryPage() {
  const [suites, setSuites] = useState<TestSuite[]>([]);
  const [filteredSuites, setFilteredSuites] = useState<TestSuite[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [isWizardOpen, setIsWizardOpen] = useState(false);
  const [selectedSuite, setSelectedSuite] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isWizardLoading, setIsWizardLoading] = useState(false);
  const [individualTests, setIndividualTests] = useState<IndividualTest[]>([]);
  const [selectedIndividualTest, setSelectedIndividualTest] = useState<IndividualTest | null>(null);

  useEffect(() => {
    Promise.all([
      testingApi.listSuites(),
      testingApi.listIndividualTests().catch(() => [])
    ])
      .then(([suitesData, testsData]) => {
        setSuites(suitesData);
        setFilteredSuites(suitesData);
        setIndividualTests(testsData);
        setIsLoading(false);
      })
      .catch((error) => {
        console.error('Failed to fetch test data:', error);
        setIsLoading(false);
      });
  }, []);

  useEffect(() => {
    if (isWizardOpen) {
      setIsWizardLoading(true);
      agentsApi
        .list({ showAll: 'true' })
        .then((data) => {
          setAgents(data);
          setIsWizardLoading(false);
        })
        .catch((error) => {
          console.error('Failed to fetch agents:', error);
          setIsWizardLoading(false);
        });
    }
  }, [isWizardOpen]);

  useEffect(() => {
    let filtered = suites;

    if (selectedCategory !== 'all') {
      filtered = filtered.filter((suite) => suite.category === selectedCategory);
    }

    if (searchQuery) {
      filtered = filtered.filter(
        (suite) =>
          suite.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          suite.description.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    setFilteredSuites(filtered);
  }, [suites, selectedCategory, searchQuery]);

  const categories = ['all', 'smoke', 'reliability', 'reasoning', 'security', 'domain'];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-display text-[var(--text-primary)]" style={{ fontSize: '32px', lineHeight: '1.2' }}>Test Library</h1>
        <p className="mt-2 text-sm text-[var(--text-muted)] font-ui">
          Browse and run quality test suites on your agents
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-muted)]" />
          <input
            type="text"
            placeholder="Search test suites..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-white/10 bg-white/5 px-10 py-2 text-sm text-[var(--text-primary)] placeholder:text-slate-500 focus:border-white/40 focus:outline-none"
          />
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-[var(--text-muted)]" />
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-[var(--text-primary)] focus:border-white/40 focus:outline-none"
          >
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat === 'all' ? 'All Categories' : cat.charAt(0).toUpperCase() + cat.slice(1)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Test Suites Grid */}
      {isLoading ? (
        <div className="py-12 text-center text-sm text-[var(--text-muted)]">Loading test suites...</div>
      ) : filteredSuites.length === 0 ? (
        <div className="py-12 text-center text-sm text-[var(--text-muted)]">
          No test suites found. Try adjusting your filters.
        </div>
      ) : (
        <div className="library-grid grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredSuites.map((suite) => (
            <Card
              key={suite.id}
              className={`library-card transition hover:border-white/20 ${suite.isRecommended ? 'border-white/20 bg-white/5' : 'border-white/10'
                }`}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="text-lg">{suite.name}</CardTitle>
                    {suite.isRecommended && (
                      <span className="mt-2 inline-block rounded-full bg-white/10 px-2 py-0.5 text-xs text-slate-300">
                        Recommended
                      </span>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <CardDescription className="mb-4">{suite.description}</CardDescription>
                <div className="mb-4 flex flex-wrap gap-2 text-xs text-[var(--text-muted)]">
                  <span>~{Math.round(suite.estimatedDurationSec / 60)} min</span>
                  <span>•</span>
                  <span>~${suite.approximateCostUsd.toFixed(2)}</span>
                  <span>•</span>
                  <span className="capitalize">{suite.category}</span>
                </div>
                <Button
                  className="w-full"
                  onClick={() => {
                    setSelectedSuite(suite.id);
                    setSelectedIndividualTest(null);
                    setIsWizardOpen(true);
                  }}
                >
                  Run on agent...
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Individual Tests Section */}
      <div className="space-y-4 border-t border-white/10 pt-8">
        <div className="flex items-center gap-2">
          <FlaskConical className="h-5 w-5 text-slate-300" />
          <h2 className="text-xl font-display text-[var(--text-primary)]">Run Individual Tests</h2>
        </div>
        <p className="text-sm text-[var(--text-muted)]">
          Select specific tests to run individually instead of running full suites.
        </p>

        <div className="flex flex-wrap items-center gap-4">
          <select
            className="flex-1 min-w-[300px] rounded-lg border border-white/10 bg-white/5 px-4 py-2 text-sm text-[var(--text-primary)] focus:border-white/40 focus:outline-none"
            onChange={(e) => {
              const test = individualTests.find(t => t.id === e.target.value);
              setSelectedIndividualTest(test || null);
            }}
            value={selectedIndividualTest?.id || ''}
          >
            <option value="">Select a test...</option>
            {individualTests.map((test) => (
              <option key={test.id} value={test.id}>
                {test.id} ({test.suiteName})
              </option>
            ))}
          </select>

          <Button
            disabled={!selectedIndividualTest}
            onClick={() => {
              setSelectedSuite(null);
              setIsWizardOpen(true);
            }}
          >
            Run Selected Test
          </Button>
        </div>
      </div>

      <TestWizardModal
        isOpen={isWizardOpen}
        onClose={() => {
          setIsWizardOpen(false);
          setSelectedSuite(null);
          setSelectedIndividualTest(null);
        }}
        agents={agents}
        suites={suites}
        individualTests={individualTests}
        isLoading={isWizardLoading}
        initialSuiteId={selectedSuite}
        initialTestId={selectedIndividualTest?.id ?? null}
        defaultMode={selectedIndividualTest ? 'individual' : 'suite'}
        onStartRun={async (agentIds, suiteIds, testIds) => {
          if (testIds && testIds.length > 0) {
            // Individual test mode: suiteIds are suite slugs
            return testingApi.startRun({
              agentId: agentIds,
              suiteId: suiteIds,
              testIds,
            });
          }

          const finalSuiteIds = selectedSuite ? [selectedSuite, ...suiteIds] : suiteIds;
          return testingApi.startRun({
            agentId: agentIds,
            suiteId: finalSuiteIds,
          });
        }}
      />
    </div>
  );
}

