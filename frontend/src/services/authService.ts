/**
 * Auth Service - Integrated with AuthContext
 */

const TOKEN_KEYS = {
  ACCESS_TOKEN: 'hr_access_token',
  REFRESH_TOKEN: 'hr_refresh_token',
  USER_DATA: 'hr_user_data',
  TOKEN_EXPIRY: 'hr_token_expiry'
};

export const authService = {
  // Get current access token
  getToken: (): string | null => {
    return localStorage.getItem(TOKEN_KEYS.ACCESS_TOKEN);
  },

  // Get refresh token
  getRefreshToken: (): string | null => {
    return localStorage.getItem(TOKEN_KEYS.REFRESH_TOKEN);
  },

  // Get user data
  getUser: (): any | null => {
    const userData = localStorage.getItem(TOKEN_KEYS.USER_DATA);
    return userData ? JSON.parse(userData) : null;
  },

  // Check if token needs refresh
  tokenNeedsRefresh: (): boolean => {
    const expiryTime = localStorage.getItem(TOKEN_KEYS.TOKEN_EXPIRY);
    if (!expiryTime) return true;

    const expiry = parseInt(expiryTime);
    const now = Date.now();
    const fiveMinutes = 5 * 60 * 1000;

    return expiry - now < fiveMinutes;
  },

  // Set auth data (called from AuthContext)
  setAuthData: (data: {
    access_token: string;
    refresh_token: string;
    expires_in?: number;
    user?: any;
  }) => {
    localStorage.setItem(TOKEN_KEYS.ACCESS_TOKEN, data.access_token);
    localStorage.setItem(TOKEN_KEYS.REFRESH_TOKEN, data.refresh_token);
    
    const expiresIn = data.expires_in || 3600;
    const expiryTime = Date.now() + (expiresIn * 1000);
    localStorage.setItem(TOKEN_KEYS.TOKEN_EXPIRY, expiryTime.toString());
    
    if (data.user) {
      localStorage.setItem(TOKEN_KEYS.USER_DATA, JSON.stringify(data.user));
    }
  },

  // Clear all auth data
  clear: () => {
    Object.values(TOKEN_KEYS).forEach(key => {
      localStorage.removeItem(key);
    });
  },

  // Clear only tokens
  clearToken: () => {
    localStorage.removeItem(TOKEN_KEYS.ACCESS_TOKEN);
    localStorage.removeItem(TOKEN_KEYS.REFRESH_TOKEN);
    localStorage.removeItem(TOKEN_KEYS.TOKEN_EXPIRY);
  },

  // Refresh token (to be called by API interceptor)
  refreshToken: async (): Promise<boolean> => {
    const refreshToken = localStorage.getItem(TOKEN_KEYS.REFRESH_TOKEN);
    if (!refreshToken) return false;

    try {
      // Import api dynamically to avoid circular dependency
      const { api } = await import('./api');
      const response = await api.auth.refreshToken();
      
      if (response.success && response.data) {
        localStorage.setItem(TOKEN_KEYS.ACCESS_TOKEN, response.data.access_token);
        
        // Update expiry
        const expiresIn = 3600; // 1 hour
        const expiryTime = Date.now() + (expiresIn * 1000);
        localStorage.setItem(TOKEN_KEYS.TOKEN_EXPIRY, expiryTime.toString());
        
        return true;
      }
      return false;
    } catch (error) {
      console.error('Token refresh failed:', error);
      return false;
    }
  }
};