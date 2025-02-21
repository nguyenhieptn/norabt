"use strict";
(self["webpackChunk"] = self["webpackChunk"] || []).push([["resources_simulation_pages_guest_RegisterView_js"],{

/***/ "./resources/simulation/pages/guest/RegisterView.js":
/*!**********************************************************!*\
  !*** ./resources/simulation/pages/guest/RegisterView.js ***!
  \**********************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react/jsx-runtime */ "./node_modules/react/jsx-runtime.js");
/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! react */ "./node_modules/react/index.js");
function _typeof(obj) { "@babel/helpers - typeof"; if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { _typeof = function _typeof(obj) { return typeof obj; }; } else { _typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return _typeof(obj); }



function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function"); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, writable: true, configurable: true } }); if (superClass) _setPrototypeOf(subClass, superClass); }

function _setPrototypeOf(o, p) { _setPrototypeOf = Object.setPrototypeOf || function _setPrototypeOf(o, p) { o.__proto__ = p; return o; }; return _setPrototypeOf(o, p); }

function _createSuper(Derived) { var hasNativeReflectConstruct = _isNativeReflectConstruct(); return function _createSuperInternal() { var Super = _getPrototypeOf(Derived), result; if (hasNativeReflectConstruct) { var NewTarget = _getPrototypeOf(this).constructor; result = Reflect.construct(Super, arguments, NewTarget); } else { result = Super.apply(this, arguments); } return _possibleConstructorReturn(this, result); }; }

function _possibleConstructorReturn(self, call) { if (call && (_typeof(call) === "object" || typeof call === "function")) { return call; } else if (call !== void 0) { throw new TypeError("Derived constructors may only return object or undefined"); } return _assertThisInitialized(self); }

function _assertThisInitialized(self) { if (self === void 0) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return self; }

function _isNativeReflectConstruct() { if (typeof Reflect === "undefined" || !Reflect.construct) return false; if (Reflect.construct.sham) return false; if (typeof Proxy === "function") return true; try { Boolean.prototype.valueOf.call(Reflect.construct(Boolean, [], function () {})); return true; } catch (e) { return false; } }

function _getPrototypeOf(o) { _getPrototypeOf = Object.setPrototypeOf ? Object.getPrototypeOf : function _getPrototypeOf(o) { return o.__proto__ || Object.getPrototypeOf(o); }; return _getPrototypeOf(o); }



var RegisterView = /*#__PURE__*/function (_Component) {
  _inherits(RegisterView, _Component);

  var _super = _createSuper(RegisterView);

  function RegisterView(props) {
    var _USER_EMAIL, _USER_MOBILE, _USER_PASSWD, _USER_PASSWD_REPEATE, _this$struct;

    var _this;

    _classCallCheck(this, RegisterView);

    _this = _super.call(this, props);
    _this.state = {};
    _this.struct = (_this$struct = {}, _defineProperty(_this$struct, USER_EMAIL, (_USER_EMAIL = {}, _defineProperty(_USER_EMAIL, INPUT_NAME, lang(USER_EMAIL)), _defineProperty(_USER_EMAIL, INPUT_TYPE, 'text'), _defineProperty(_USER_EMAIL, INPUT_NULL, false), _defineProperty(_USER_EMAIL, INPUT_VALIDATE, 'email'), _USER_EMAIL)), _defineProperty(_this$struct, USER_MOBILE, (_USER_MOBILE = {}, _defineProperty(_USER_MOBILE, INPUT_NAME, lang(USER_MOBILE)), _defineProperty(_USER_MOBILE, INPUT_TYPE, 'text'), _defineProperty(_USER_MOBILE, INPUT_NULL, false), _USER_MOBILE)), _defineProperty(_this$struct, USER_PASSWD, (_USER_PASSWD = {}, _defineProperty(_USER_PASSWD, INPUT_NAME, lang(USER_PASSWD)), _defineProperty(_USER_PASSWD, INPUT_TYPE, 'password'), _defineProperty(_USER_PASSWD, INPUT_NULL, false), _USER_PASSWD)), _defineProperty(_this$struct, 'USER_PASSWD_REPEATE', (_USER_PASSWD_REPEATE = {}, _defineProperty(_USER_PASSWD_REPEATE, INPUT_NAME, lang('Nhập lại Mật khẩu')), _defineProperty(_USER_PASSWD_REPEATE, INPUT_TYPE, 'password'), _defineProperty(_USER_PASSWD_REPEATE, INPUT_NULL, false), _USER_PASSWD_REPEATE)), _this$struct);
    return _this;
  }

  _createClass(RegisterView, [{
    key: "render",
    value: function render() {
      return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
        className: "box_flex",
        style: {
          justifyContent: 'center'
        },
        children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
          className: "box_flex",
          style: {
            maxWidth: 400
          },
          children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
            className: "box_flex",
            style: {
              justifyContent: 'center'
            },
            children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("img", {
              src: {
                AP: AP
              }
            })
          })
        })
      });
    }
  }]);

  return RegisterView;
}(react__WEBPACK_IMPORTED_MODULE_1__.Component);

/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (RegisterView);

/***/ })

}]);