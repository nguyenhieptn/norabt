"use strict";
(self["webpackChunk"] = self["webpackChunk"] || []).push([["resources_react_pages_control_ControlView_js"],{

/***/ "./resources/react/pages/control/ControlView.js":
/*!******************************************************!*\
  !*** ./resources/react/pages/control/ControlView.js ***!
  \******************************************************/
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



var Control = /*#__PURE__*/function (_Component) {
  _inherits(Control, _Component);

  var _super = _createSuper(Control);

  function Control(props) {
    var _control_app_name, _control_title, _control_app_icon;

    var _this;

    _classCallCheck(this, Control);

    _this = _super.call(this, props);
    _this.state = {
      content: ''
    };
    _this.struct = {
      'control_app_name': (_control_app_name = {}, _defineProperty(_control_app_name, INPUT_NAME, lang('App Name')), _defineProperty(_control_app_name, INPUT_TYPE, 'text'), _control_app_name),
      'control_title': (_control_title = {}, _defineProperty(_control_title, INPUT_NAME, lang('Title')), _defineProperty(_control_title, INPUT_TYPE, 'text'), _control_title),
      'control_app_icon': (_control_app_icon = {}, _defineProperty(_control_app_icon, INPUT_NAME, lang('App Icon')), _defineProperty(_control_app_icon, INPUT_TYPE, 'image'), _defineProperty(_control_app_icon, INPUT_EXTEND, {
        'fileManager': function fileManager() {
          return _this.fileManager;
        }
      }), _control_app_icon)
    };
    return _this;
  }

  _createClass(Control, [{
    key: "render",
    value: function render() {
      return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.Fragment, {
        children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
          className: "box_shadow box_padding"
        })
      });
    }
  }, {
    key: "componentDidMount",
    value: function componentDidMount() {
      this.loadData();
    }
  }, {
    key: "loadData",
    value: function loadData() {
      var _this2 = this;

      App.loading(true, 'Loading...');
      return axios.request({
        url: '/control/control/read',
        method: 'post',
        data: {
          keys: ['control_logo', 'control_app_icon', 'control_title', 'control_app_name']
        }
      }).then(function (response) {
        App.loading(false, 'Adding...');
        response = response['data'];

        if (response['result']) {
          _this2.form.setValue(response['data']);

          if (isset(response['data']['control_logo'])) {
            if (_this2.editor) _this2.editor.editor.setData(response['data']['control_logo']);

            _this2.setState({
              content: response['data']['control_logo']
            });
          }
        } else {
          return Promise.reject(response);
        }
      })["catch"](function (error) {
        console.log(error);
        App.loading(false, 'Adding...');
        error_handle(error);
      });
    }
  }, {
    key: "updateData",
    value: function updateData(data) {
      App.loading(true, 'Loading...');
      return axios.request({
        url: '/control/control/update',
        method: 'post',
        data: data
      }).then(function (response) {
        App.loading(false, 'Adding...');
        response = response['data'];

        if (response['result']) {
          Swal(true, 'Success', 'success');
        } else {
          error_handle(response);
        }
      })["catch"](function (error) {
        console.log(error);
        App.loading(false, 'Adding...');
        error_handle(error);
      });
    }
  }]);

  return Control;
}(react__WEBPACK_IMPORTED_MODULE_1__.Component);

/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (Control);

/***/ })

}]);