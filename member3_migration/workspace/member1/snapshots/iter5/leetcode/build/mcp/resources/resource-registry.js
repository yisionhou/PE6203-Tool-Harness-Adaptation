import { RegistryBase } from "../../common/registry-base.js";
/**
 * Base registry class for LeetCode resources that provides site type detection and authentication status checks.
 * This abstract class defines the framework for registering different categories of resources based on
 * site version (Global or CN) and authentication requirements.
 */
export class ResourceRegistry extends RegistryBase {
    server;
    leetcodeService;
    /**
     * Creates a new resource registry instance.
     *
     * @param server - The MCP server instance to register resources with
     * @param leetcodeService - The LeetCode service implementation to use for API calls
     */
    constructor(server, leetcodeService) {
        super(server, leetcodeService);
        this.server = server;
        this.leetcodeService = leetcodeService;
    }
    /**
     * Registers all applicable resources based on site version and authentication status.
     */
    registerResources() {
        this.register();
    }
}
//# sourceMappingURL=resource-registry.js.map