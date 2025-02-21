"use strict";
(self["webpackChunk"] = self["webpackChunk"] || []).push([["./react/pages/admin-Lab_strategies_groupView-js"],{

/***/ "./resources/simulation/pages/admin/Lab_strategies_groupView.js":
/*!**********************************************************************!*\
  !*** ./resources/simulation/pages/admin/Lab_strategies_groupView.js ***!
  \**********************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react/jsx-runtime */ "./node_modules/react/jsx-runtime.js");
/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! react */ "./node_modules/react/index.js");
/* harmony import */ var _model_admin_Lab_strategies__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ../../model/admin/Lab_strategies */ "./resources/simulation/model/admin/Lab_strategies.js");
/* harmony import */ var _assets_img_folder_webp__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ../../../assets/img/folder.webp */ "./resources/assets/img/folder.webp");
/* harmony import */ var _model_admin_Lab_account__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! ../../model/admin/Lab_account */ "./resources/simulation/model/admin/Lab_account.js");
function _typeof(obj) { "@babel/helpers - typeof"; if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { _typeof = function _typeof(obj) { return typeof obj; }; } else { _typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return _typeof(obj); }




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






var Lab_strategies_groupView = /*#__PURE__*/function (_Component) {
  _inherits(Lab_strategies_groupView, _Component);

  var _super = _createSuper(Lab_strategies_groupView);

  function Lab_strategies_groupView(props) {
    var _this;

    _classCallCheck(this, Lab_strategies_groupView);

    _this = _super.call(this, props);
    _this.state = {
      group: {}
    };
    _this.model = new _model_admin_Lab_strategies__WEBPACK_IMPORTED_MODULE_2__.default();
    _this.labAccountModel = new _model_admin_Lab_account__WEBPACK_IMPORTED_MODULE_4__.default();
    return _this;
  }

  _createClass(Lab_strategies_groupView, [{
    key: "componentDidMount",
    value: function componentDidMount() {
      var _this2 = this;

      this.model.getGroup().then(function (res) {
        _this2.setState({
          group: res['data']
        });
      });
    }
  }, {
    key: "click",
    value: function click(item) {
      window.location.href = App.link('/admin/lab_strategies/view?group=' + item);
    }
  }, {
    key: "changeGroupnameFu",
    value: function changeGroupnameFu(newGr, oldGr) {
      return this.labAccountModel.changeGroupName(newGr, oldGr);
    }
  }, {
    key: "render",
    value: function render() {
      var _this3 = this;

      return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
        style: {
          display: 'flex',
          flexWrap: 'wrap'
        },
        children: Object.keys(this.state.group).map(function (item) {
          return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(GroupFolder, {
            name: item,
            onClick: _this3.click.bind(_this3),
            onChangeFolder: function onChangeFolder(newGr, oldGr) {
              return _this3.changeGroupnameFu(newGr, oldGr);
            }
          }, item);
        })
      });
    }
  }]);

  return Lab_strategies_groupView;
}(react__WEBPACK_IMPORTED_MODULE_1__.Component);

/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (Lab_strategies_groupView);

var GroupFolder = /*#__PURE__*/function (_Component2) {
  _inherits(GroupFolder, _Component2);

  var _super2 = _createSuper(GroupFolder);

  function GroupFolder(props) {
    var _this4;

    _classCallCheck(this, GroupFolder);

    _this4 = _super2.call(this, props);
    _this4.state = {
      name: _this4.props.name,
      edit: false
    };
    _this4.originName = _this4.props.name;
    return _this4;
  }

  _createClass(GroupFolder, [{
    key: "onBlur",
    value: function onBlur() {
      var _this5 = this;

      if (this.state.name == this.originName) {
        this.setState({
          edit: false
        });
        return;
      }

      if (this.props.onChangeFolder) {
        this.props.onChangeFolder(this.state.name, this.originName).then(function (res) {
          if (!res['result']) {
            _this5.setState({
              name: _this5.originName
            });
          } else {
            _this5.originName = _this5.state.name;

            _this5.setState({
              edit: false
            });
          }
        });
      }
    }
  }, {
    key: "render",
    value: function render() {
      var _this6 = this;

      return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
        style: {
          marginRight: '30px',
          cursor: 'pointer'
        },
        children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("img", {
          onClick: function onClick() {
            return _this6.props.onClick(_this6.state.name);
          },
          src: _assets_img_folder_webp__WEBPACK_IMPORTED_MODULE_3__.default,
          style: {
            width: '100px',
            cursor: 'pointer'
          },
          alt: "fireSpot"
        }), this.state.edit ? /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
          children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("input", {
            ref: function ref(c) {
              return _this6.input = c;
            },
            className: "input",
            type: "text",
            value: this.state.name,
            onChange: function onChange(e) {
              return _this6.setState({
                name: e.target.value
              });
            },
            onBlur: function onBlur() {
              _this6.onBlur();
            }
          })
        }) : /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
          style: {
            textAlign: 'center',
            cursor: 'pointer'
          },
          onDoubleClick: function onDoubleClick() {
            _this6.setState({
              edit: true
            }, function () {
              _this6.input.focus();
            });
          },
          children: this.state.name
        })]
      });
    }
  }]);

  return GroupFolder;
}(react__WEBPACK_IMPORTED_MODULE_1__.Component);

/***/ }),

/***/ "./resources/assets/img/folder.webp":
/*!******************************************!*\
  !*** ./resources/assets/img/folder.webp ***!
  \******************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = ("/images/folder.webp?83c41d4c7acc24c56cf7bcd88ff89ffb");

/***/ })

}]);