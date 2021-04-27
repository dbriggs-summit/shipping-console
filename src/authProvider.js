import configData from './config.json';

const authProvider = {
    // authentication
    login: ({ username, password }) =>  {
        const request = new Request(configData.apiUrl + 'login', {
            method: 'POST',
            body: JSON.stringify({ username, password }),
            headers: new Headers({ 'Content-Type': 'application/json' }),
        });
        return fetch(request)
            .then(response => {
                if (response.status < 200 || response.status >= 300) {
                    throw new Error(response.statusText);
                }
                return response.json();
            })
            .then(auth => {
                localStorage.setItem('auth', JSON.stringify(auth));
            })
            .catch(() => {
                throw new Error('Network error')
            });
    },
    checkError: (error) => {
        const status = error.status;
        if (status === 401 || status === 403) {
            localStorage.removeItem('auth');
            return Promise.reject();
        }
        // other error code (404, 500, etc): no need to log out
        return Promise.resolve();
    },
    checkAuth: () => localStorage.getItem('auth')
        ? Promise.resolve()
        : Promise.reject(), //Change this to Promise.reject() if you want to require login
    logout: () => {
        localStorage.removeItem('auth');
        return Promise.resolve();
    },
    getIdentity: () => {
        try {
            const { id, fullName } = JSON.parse(localStorage.getItem('auth'));
            return Promise.resolve({ id, fullName });
        } catch (error) {
            return Promise.reject(error);
        }
    },
    // authorization
    getPermissions: params => {
        try {
            const {id, fullName} = JSON.parse(localStorage.getItem('auth'));
            return Promise.resolve(id);
        } catch (error) {
            return Promise.resolve('guest');
        }
    }
};

export default authProvider;