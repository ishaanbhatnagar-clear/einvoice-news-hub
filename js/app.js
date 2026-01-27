/**
 * eInvoice News Hub - Main Application
 * Alpine.js based frontend for displaying aggregated e-invoicing news
 */

function newsApp() {
    return {
        // State
        loading: true,
        newsData: {
            lastUpdated: null,
            crawlStatus: 'unknown',
            articles: []
        },
        regions: [],
        sources: [],
        categories: [],
        filteredArticles: [],

        // Filters (multi-select arrays)
        selectedRegions: [],
        selectedSources: [],
        selectedCategories: [],
        filters: {
            timeRange: ''
        },
        searchQuery: '',

        // Country flags mapping
        countryFlags: {},

        /**
         * Initialize the application
         */
        async init() {
            // Check authentication
            if (!checkAuth()) {
                return;
            }

            try {
                // Load data files in parallel
                const [newsResponse, regionsResponse, sourcesResponse] = await Promise.all([
                    fetch('data/news.json'),
                    fetch('data/regions.json'),
                    fetch('data/sources.json')
                ]);

                this.newsData = await newsResponse.json();
                const regionsData = await regionsResponse.json();
                const sourcesData = await sourcesResponse.json();

                this.regions = regionsData.regions;
                this.sources = sourcesData.sources;
                this.categories = sourcesData.categories;

                // Build country flags map
                this.buildCountryFlagsMap();

                // Initial filter
                this.filterNews();

            } catch (error) {
                console.error('Failed to load data:', error);
            } finally {
                this.loading = false;
            }
        },

        /**
         * Build a map of country codes to flags
         */
        buildCountryFlagsMap() {
            this.regions.forEach(region => {
                region.countries.forEach(country => {
                    this.countryFlags[country.code] = country.flag;
                });
            });
        },

        /**
         * Filter news based on current filters and search query
         */
        filterNews() {
            let articles = [...this.newsData.articles];

            // Filter by regions (multi-select)
            if (this.selectedRegions.length > 0) {
                articles = articles.filter(a => this.selectedRegions.includes(a.region));
            }

            // Filter by sources (multi-select)
            if (this.selectedSources.length > 0) {
                articles = articles.filter(a => this.selectedSources.includes(a.source.id));
            }

            // Filter by categories (multi-select)
            if (this.selectedCategories.length > 0) {
                articles = articles.filter(a =>
                    a.categories.some(cat => this.selectedCategories.includes(cat))
                );
            }

            // Filter by time range
            if (this.filters.timeRange) {
                const days = parseInt(this.filters.timeRange);
                const cutoff = new Date();
                cutoff.setDate(cutoff.getDate() - days);
                articles = articles.filter(a => new Date(a.publishedAt) >= cutoff);
            }

            // Filter by search query
            if (this.searchQuery.trim()) {
                const query = this.searchQuery.toLowerCase();
                articles = articles.filter(a =>
                    a.title.toLowerCase().includes(query) ||
                    a.summary.toLowerCase().includes(query) ||
                    a.countryName?.toLowerCase().includes(query) ||
                    a.source.name.toLowerCase().includes(query)
                );
            }

            // Sort by date (newest first)
            articles.sort((a, b) => new Date(b.publishedAt) - new Date(a.publishedAt));

            this.filteredArticles = articles;
        },

        /**
         * Check if any filters are active
         */
        hasActiveFilters() {
            return this.selectedRegions.length > 0 ||
                   this.selectedSources.length > 0 ||
                   this.selectedCategories.length > 0 ||
                   this.filters.timeRange ||
                   this.searchQuery.trim();
        },

        /**
         * Clear all filters
         */
        clearFilters() {
            this.selectedRegions = [];
            this.selectedSources = [];
            this.selectedCategories = [];
            this.filters = {
                timeRange: ''
            };
            this.searchQuery = '';
            this.filterNews();
        },

        /**
         * SECTION 1: Government News - official sources only
         */
        getGovtNews() {
            return this.filteredArticles.filter(a => a.source.type === 'official');
        },

        /**
         * SECTION 2: Other Sources - advisory, news outlets, aggregators, social
         */
        getOtherNews() {
            const otherTypes = ['advisory', 'news', 'aggregator', 'social'];
            return this.filteredArticles.filter(a => otherTypes.includes(a.source.type));
        },

        /**
         * SECTION 3: Vendor News - vendors and taxtech
         */
        getVendorNews() {
            const vendorTypes = ['vendor', 'taxtech'];
            return this.filteredArticles.filter(a => vendorTypes.includes(a.source.type));
        },

        /**
         * Get unique countries from government news
         */
        getGovtCountries() {
            const govtNews = this.getGovtNews();
            const countries = new Map();
            govtNews.forEach(a => {
                if (a.country && !countries.has(a.country)) {
                    countries.set(a.country, {
                        code: a.country,
                        name: a.countryName,
                        flag: this.getCountryFlag(a.country)
                    });
                }
            });
            return Array.from(countries.values());
        },

        /**
         * Get government news by country
         */
        getGovtNewsByCountry(countryCode) {
            return this.getGovtNews().filter(a => a.country === countryCode);
        },

        /**
         * Get country flag emoji
         */
        getCountryFlag(countryCode) {
            if (!countryCode) return '🌐';
            return this.countryFlags[countryCode] || '🌐';
        },

        /**
         * Get category color
         */
        getCategoryColor(category) {
            const cat = this.categories.find(c => c.id === category);
            return cat ? cat.color : '#6B7280';
        },

        /**
         * Format date for display
         */
        formatDate(dateStr) {
            if (!dateStr) return 'Unknown';
            const date = new Date(dateStr);
            return date.toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                timeZoneName: 'short'
            });
        },

        /**
         * Get relative time string
         */
        getRelativeTime(dateStr) {
            if (!dateStr) return '';

            const date = new Date(dateStr);
            const now = new Date();
            const diffMs = now - date;
            const diffSecs = Math.floor(diffMs / 1000);
            const diffMins = Math.floor(diffSecs / 60);
            const diffHours = Math.floor(diffMins / 60);
            const diffDays = Math.floor(diffHours / 24);

            if (diffSecs < 60) return 'Just now';
            if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
            if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
            if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
            if (diffDays < 30) return `${Math.floor(diffDays / 7)} week${Math.floor(diffDays / 7) > 1 ? 's' : ''} ago`;

            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        },

        /**
         * Logout user
         */
        logout() {
            if (typeof window.logout === 'function') {
                window.logout();
            } else {
                localStorage.removeItem('einvoice-auth');
                localStorage.removeItem('einvoice-auth-expiry');
                window.location.href = 'login.html';
            }
        }
    };
}
