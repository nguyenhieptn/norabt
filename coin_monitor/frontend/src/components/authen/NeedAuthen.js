const NeedAuthen = ({ children }) => {
    if (!global.USER) {
      window.location.href = `/admin/login/?next=${encodeURIComponent(window.location.href)}`
    }
    return children;
} 

export default NeedAuthen