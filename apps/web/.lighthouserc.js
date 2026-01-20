module.exports = {
    ci: {
        collect: {
            startServerCommand: 'npm run start',
            url: ['http://localhost:3000', 'http://localhost:3000/agents'],
            numberOfRuns: 3,
        },
        upload: {
            target: 'temporary-public-storage',
        },
        assert: {
            assertions: {
                'categories:performance': ['error', { minScore: 0.9 }],
                'categories:accessibility': ['error', { minScore: 0.95 }],
                'categories:best-practices': ['error', { minScore: 0.9 }],
                'categories:seo': ['error', { minScore: 0.9 }],
            },
        },
    },
};
