/**
 * Abstract base registry class for LeetCode components that provides site type detection and authentication status checks.
 * This class defines the framework for registering different categories of components based on
 * site version (Global or CN) and authentication requirements.
 */
export class RegistryBase {
    server;
    leetcodeService;
    /**
     * Creates a new registry instance.
     *
     * @param server - The MCP server instance to register components with
     * @param leetcodeService - The LeetCode service implementation to use for API calls
     */
    constructor(server, leetcodeService) {
        this.server = server;
        this.leetcodeService = leetcodeService;
    }
    /**
     * Determines if the current LeetCode service is for the China version.
     *
     * @returns True if the service is for LeetCode CN, false otherwise
     */
    isCN() {
        return this.leetcodeService.isCN();
    }
    /**
     * Determines if the current LeetCode service has valid authentication credentials.
     *
     * @returns True if authenticated, false otherwise
     */
    isAuthenticated() {
        return this.leetcodeService.isAuthenticated();
    }
    /**
     * Registers all applicable components based on site version and authentication status.
     * This method follows a specific registration sequence to ensure proper component organization.
     */
    register() {
        // 1. Register unauthenticated common components (available on both Global and CN)
        this.registerCommon();
        // 2. Register unauthenticated site-specific components based on site version
        if (this.isCN()) {
            this.registerChina();
        }
        else {
            this.registerGlobal();
        }
        // 3. Register authenticated components only if authentication credentials are available
        if (this.isAuthenticated()) {
            this.registerAuthenticatedCommon();
            if (this.isCN()) {
                this.registerAuthenticatedChina();
            }
            else {
                this.registerAuthenticatedGlobal();
            }
        }
    }
    /**
     * Registers common components available on both Global and CN platforms that don't require authentication.
     * Implementing classes must define this method to register their specific common components.
     */
    registerCommon() { }
    /**
     * Registers components specific to the Global LeetCode site that don't require authentication.
     * Implementing classes must define this method to register their Global-specific components.
     */
    registerGlobal() { }
    /**
     * Registers components specific to the China LeetCode site that don't require authentication.
     * Implementing classes must define this method to register their China-specific components.
     */
    registerChina() { }
    /**
     * Registers common components available on both Global and CN platforms that require authentication.
     * Implementing classes must define this method to register their authenticated common components.
     */
    registerAuthenticatedCommon() { }
    /**
     * Registers components specific to the Global LeetCode site that require authentication.
     * Implementing classes must define this method to register their authenticated Global-specific components.
     */
    registerAuthenticatedGlobal() { }
    /**
     * Registers components specific to the China LeetCode site that require authentication.
     * Implementing classes must define this method to register their authenticated China-specific components.
     */
    registerAuthenticatedChina() { }
}
//# sourceMappingURL=registry-base.js.map