"use strict";
(self["webpackChunk"] = self["webpackChunk"] || []).push([["resources_simulation_pages_user_PagesProduct_js"],{

/***/ "./resources/simulation/components/user/InputVoucherOption.js":
/*!********************************************************************!*\
  !*** ./resources/simulation/components/user/InputVoucherOption.js ***!
  \********************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react/jsx-runtime */ "./node_modules/react/jsx-runtime.js");
/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! react */ "./node_modules/react/index.js");
function _typeof(obj) { "@babel/helpers - typeof"; if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { _typeof = function _typeof(obj) { return typeof obj; }; } else { _typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return _typeof(obj); }



var _excluded = ["onChange", "onFocus", "option", "onApply", "onBlur"];

function ownKeys(object, enumerableOnly) { var keys = Object.keys(object); if (Object.getOwnPropertySymbols) { var symbols = Object.getOwnPropertySymbols(object); if (enumerableOnly) { symbols = symbols.filter(function (sym) { return Object.getOwnPropertyDescriptor(object, sym).enumerable; }); } keys.push.apply(keys, symbols); } return keys; }

function _objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i] != null ? arguments[i] : {}; if (i % 2) { ownKeys(Object(source), true).forEach(function (key) { _defineProperty(target, key, source[key]); }); } else if (Object.getOwnPropertyDescriptors) { Object.defineProperties(target, Object.getOwnPropertyDescriptors(source)); } else { ownKeys(Object(source)).forEach(function (key) { Object.defineProperty(target, key, Object.getOwnPropertyDescriptor(source, key)); }); } } return target; }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

function _objectWithoutProperties(source, excluded) { if (source == null) return {}; var target = _objectWithoutPropertiesLoose(source, excluded); var key, i; if (Object.getOwnPropertySymbols) { var sourceSymbolKeys = Object.getOwnPropertySymbols(source); for (i = 0; i < sourceSymbolKeys.length; i++) { key = sourceSymbolKeys[i]; if (excluded.indexOf(key) >= 0) continue; if (!Object.prototype.propertyIsEnumerable.call(source, key)) continue; target[key] = source[key]; } } return target; }

function _objectWithoutPropertiesLoose(source, excluded) { if (source == null) return {}; var target = {}; var sourceKeys = Object.keys(source); var key, i; for (i = 0; i < sourceKeys.length; i++) { key = sourceKeys[i]; if (excluded.indexOf(key) >= 0) continue; target[key] = source[key]; } return target; }

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



var InputVoucherOption = /*#__PURE__*/function (_Component) {
  _inherits(InputVoucherOption, _Component);

  var _super = _createSuper(InputVoucherOption);

  function InputVoucherOption(props) {
    var _this;

    _classCallCheck(this, InputVoucherOption);

    _this = _super.call(this, props);
    _this.id = makeId();
    _this.state = {
      value: get(_this.props.value, ''),
      show: false
    };
    _this.closeOptionBar = _this.closeOptionBar.bind(_assertThisInitialized(_this));
    _this.oldValue = _this.state.value;
    return _this;
  }

  _createClass(InputVoucherOption, [{
    key: "initial",
    value: function initial() {
      var _this$props = this.props,
          onChange = _this$props.onChange,
          onFocus = _this$props.onFocus,
          option = _this$props.option,
          onApply = _this$props.onApply,
          onBlur = _this$props.onBlur,
          rent = _objectWithoutProperties(_this$props, _excluded);

      this.onChange = get(onChange, function () {});
      this.onFocus = get(onFocus, function () {});
      this.rent = rent;
    }
  }, {
    key: "setValue",
    value: function setValue(value) {
      if (value == null) value = '';
      this.setState({
        value: value
      });
    }
  }, {
    key: "getValue",
    value: function getValue() {
      var value = this.state.value;
      return value;
    }
  }, {
    key: "openOptionBar",
    value: function openOptionBar(event) {
      var newState = true;
      this.setState({
        show: newState
      });

      if (newState) {
        window.addEventListener('click', this.closeOptionBar);
      }

      event.stopPropagation();
    }
  }, {
    key: "closeOptionBar",
    value: function closeOptionBar(event) {
      if (event.target.closest("#option".concat(this.id)) == null) {
        this.setState({
          show: false
        });
        window.removeEventListener('click', this.closeOptionBar);
        event.stopPropagation();
        event.preventDefault();
      }
    }
  }, {
    key: "componentWillUnmount",
    value: function componentWillUnmount() {
      window.removeEventListener('click', this.closeOptionBar);
    }
  }, {
    key: "getVoucher",
    value: function getVoucher() {
      var _this2 = this;

      if (this.state.value == this.oldValue) return;
      this.oldValue = this.state.value;

      if (this.state.value == '') {
        if (this.props.onApply) this.props.onApply(_defineProperty({}, VOUCHER_VALUE, 0));
        return;
      }

      App.loading(true);
      axios({
        method: 'POST',
        url: '/user/pages/getVoucher',
        dataType: 'json',
        data: {
          voucher: this.state.value
        }
      }).then(function (response) {
        App.loading(false);
        response = response.data;

        if (response['result']) {
          if (_this2.props.onApply) _this2.props.onApply(response['data']);
        } else {
          if (_this2.props.onApply) _this2.props.onApply(_defineProperty({}, VOUCHER_VALUE, 0));
          error_handle(response);
        }
      })["catch"](function (error) {
        App.loading(false);
        console.log(error);
        if (_this2.props.onApply) _this2.props.onApply(_defineProperty({}, VOUCHER_VALUE, 0));
        error_handle(error);
      });
    }
  }, {
    key: "render",
    value: function render() {
      var _this3 = this;

      this.initial();
      return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
        className: "input_option",
        style: {
          position: 'relative'
        },
        children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("input", _objectSpread({
          value: this.state.value,
          onChange: function onChange(event) {
            _this3.setState({
              value: event.target.value
            });
          },
          onFocus: function onFocus(event) {
            _this3.openOptionBar(event);
          },
          onClick: function onClick(e) {
            e.stopPropagation();
          },
          onBlur: function onBlur() {
            _this3.getVoucher();
          },
          ref: function ref(input) {
            return _this3.input = input;
          }
        }, this.rent)), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
          id: "option".concat(this.id),
          className: "box_shadow",
          style: {
            display: this.state.show ? 'block' : 'none',
            position: 'absolute',
            left: 0,
            padding: 5,
            background: 'white',
            zIndex: 1
          },
          children: Object.keys(this.props.option).map(function (item) {
            return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
              className: "box_flex button box_line",
              style: {
                padding: 5
              },
              onClick: function onClick(e) {
                _this3.setState({
                  value: item,
                  show: false
                }, function () {
                  _this3.getVoucher();
                });
              },
              children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("i", {
                className: "fa fa-tag"
              }), "\xA0 ", /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("b", {
                children: item
              }), "\xA0", "(Gi\u1EA3m gi\xE1 ".concat(_this3.props.option[item], " VN\u0110)")]
            }, item);
          })
        }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("style", {
          children: "\n\t\t\t\t\t\t.input_option::after{\n\t\t\t\t\t\t\tcontent: \"\\f0d7\";\n\t\t\t\t\t\t\tfont: normal normal normal 14px/1 FontAwesome;\n\t\t\t\t\t\t\tposition: absolute;\n\t\t\t\t\t\t\tright: 5px;\n\t\t\t\t\t\t\ttop: 5px;\n\t\t\t\t\t\t}\n\t\t\t\t\t"
        })]
      });
    }
  }]);

  return InputVoucherOption;
}(react__WEBPACK_IMPORTED_MODULE_1__.Component);

/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (InputVoucherOption);

/***/ }),

/***/ "./resources/simulation/pages/user/PagesProduct.js":
/*!*********************************************************!*\
  !*** ./resources/simulation/pages/user/PagesProduct.js ***!
  \*********************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react/jsx-runtime */ "./node_modules/react/jsx-runtime.js");
/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! react */ "./node_modules/react/index.js");
/* harmony import */ var _components_user_css_responsive_scss__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! ../../components/user/css/responsive.scss */ "./resources/simulation/components/user/css/responsive.scss");
/* harmony import */ var _components_user_InputVoucherOption__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ../../components/user/InputVoucherOption */ "./resources/simulation/components/user/InputVoucherOption.js");
/* harmony import */ var react_router_dom__WEBPACK_IMPORTED_MODULE_4__ = __webpack_require__(/*! react-router-dom */ "./node_modules/react-router-dom/es/withRouter.js");
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






var PagesHome = /*#__PURE__*/function (_Component) {
  _inherits(PagesHome, _Component);

  var _super = _createSuper(PagesHome);

  function PagesHome(props) {
    var _this;

    _classCallCheck(this, PagesHome);

    _this = _super.call(this, props);
    _this.state = {
      product: {},
      mainImage: '',
      vouchers: {},
      voucher: 0,
      quantity: 1,
      venders: {},
      note: ''
    };
    _this.pid = get(App.parsed['id'], '');
    return _this;
  }

  _createClass(PagesHome, [{
    key: "componentDidMount",
    value: function componentDidMount() {
      this.loadProduct();
      this.loadMapping();
    }
  }, {
    key: "loadMapping",
    value: function loadMapping() {
      var _this2 = this;

      axios({
        method: 'POST',
        url: '/user/pages/getProductMapping',
        dataType: 'json',
        data: _defineProperty({}, PRODUCT_ID, this.pid)
      }).then(function (response) {
        App.loading(false);
        response = response.data;

        if (response['result']) {
          var data = response['data'];

          _this2.setState({
            vouchers: data[VOUCHERS_TABLE],
            venders: data[VENDERS_TABLE]
          });
        } else {
          error_handle(response);
        }
      })["catch"](function (error) {
        App.loading(false);
        console.log(error);
        error_handle(error.response);
      });
    }
  }, {
    key: "loadProduct",
    value: function loadProduct() {
      var _this3 = this;

      App.loading(true);
      axios({
        method: 'POST',
        url: '/user/pages/getProduct',
        dataType: 'json',
        data: _defineProperty({}, PRODUCT_ID, this.pid)
      }).then(function (response) {
        App.loading(false);
        response = response.data;

        if (response['result']) {
          if (isset(response['data'][0])) {
            _this3.setState({
              product: response['data'][0],
              mainImage: response['data'][0][PRODUCT_IMAGE]
            });
          }
        } else {
          error_handle(response);
        }
      })["catch"](function (error) {
        App.loading(false);
        console.log(error);
        error_handle(error.response);
      });
    }
  }, {
    key: "order",
    value: function order() {
      var _data3,
          _this4 = this;

      App.loading(true);
      axios({
        method: 'POST',
        url: '/user/pages/order',
        dataType: 'json',
        data: (_data3 = {}, _defineProperty(_data3, ORDER_PID, this.pid), _defineProperty(_data3, ORDER_PNUMBER, this.state.quantity), _defineProperty(_data3, ORDER_VCODE, this.voucherInput.getValue()), _defineProperty(_data3, ORDER_NOTE, this.state.note), _data3)
      }).then(function (response) {
        App.loading(false);
        response = response.data;

        if (response['result']) {
          swal({
            html: response['data'],
            showCloseButton: false,
            showCancelButton: false,
            showConfirmButton: true,
            onClose: function onClose() {
              _this4.props.history.push('/user/pages/home');
            }
          }).then(function () {});
        } else {
          error_handle(response);
        }
      })["catch"](function (error) {
        App.loading(false);
        console.log(error);
        error_handle(error.response);
      });
    }
  }, {
    key: "render",
    value: function render() {
      var _this5 = this;

      console.log(this.state.product);
      if (!isset(this.state.product[PRODUCT_ID])) return '';
      var vender = this.state.venders[this.state.product[PRODUCT_VENDER]];
      var venderName = vender ? vender[VENDER_NAME] : '';
      var venderImg = vender ? file_public(vender[VENDER_IMAGE]) : '';

      if (this.state.product[PRODUCT_PROMOTION] != '' && this.state.product[PRODUCT_PROMOTION] != null) {
        var listPromotion = this.state.product[PRODUCT_PROMOTION].split("\n");

        var productPromotion = /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
          className: "box_border",
          style: {
            borderColor: '#ccc',
            borderRadius: 5,
            marginTop: 10
          },
          children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
            style: {
              borderBottom: 'solid thin #ccc',
              padding: 5,
              background: '#eee',
              fontWeight: 'bold'
            },
            children: "Khuy\u1EBFn m\xE3i \xE1p d\u1EE5ng"
          }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
            className: "box_padding",
            children: listPromotion.map(function (item, key) {
              return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                style: {
                  padding: '3px 0px'
                },
                children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("i", {
                  className: "fa fa-check-square",
                  style: {
                    color: 'green'
                  }
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  style: {
                    display: 'inline-block',
                    paddingLeft: 5
                  },
                  children: item
                })]
              }, key);
            })
          })]
        });
      } else {
        var productPromotion = '';
      }

      return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
        className: "container product_page",
        style: {
          padding: 0
        },
        children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
          className: "row",
          children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
            className: "col-md-6",
            children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
              className: "product_page_image_frame",
              children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  className: "box_line title",
                  children: this.state.product[PRODUCT_NAME]
                })
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                className: "product_page_image_active",
                children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("img", {
                  style: {
                    width: '80%',
                    height: '100%',
                    objectFit: 'contain'
                  },
                  src: this.state.mainImage == '' ? '' : file_public(this.state.mainImage)
                })
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                className: "box_flex",
                style: {
                  justifyContent: 'center'
                },
                children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  className: "product_page_image_child box_shadow ".concat(this.state.product[PRODUCT_IMAGE] == this.state.mainImage ? 'active' : ''),
                  onClick: function onClick() {
                    _this5.setState({
                      mainImage: _this5.state.product[PRODUCT_IMAGE]
                    });
                  },
                  children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("img", {
                    style: {
                      width: '100%',
                      height: '100%',
                      objectFit: 'contain'
                    },
                    src: file_public(this.state.product[PRODUCT_IMAGE])
                  })
                }), this.state.product[PRODUCT_IMAGES_TABLE].map(function (item) {
                  return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                    className: "product_page_image_child box_shadow ".concat(item[PRODUCT_IMG_PATH] == _this5.state.mainImage ? 'active' : ''),
                    onClick: function onClick() {
                      _this5.setState({
                        mainImage: item[PRODUCT_IMG_PATH]
                      });
                    },
                    children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("img", {
                      style: {
                        width: '100%',
                        height: '100%',
                        objectFit: 'contain'
                      },
                      src: file_public(item[PRODUCT_IMG_PATH])
                    })
                  }, item[PRODUCT_IMG_ID]);
                })]
              })]
            })
          }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
            className: "col-md-6",
            children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
              children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                className: "product_item_name",
                title: this.state.product[PRODUCT_NAME],
                children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("b", {
                  children: this.state.product[PRODUCT_NAME]
                })
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                children: ["M\xE3 S\u1EA3n ph\u1EA9m: ", /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("strong", {
                  children: this.state.product[PRODUCT_MODEL]
                })]
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                children: ["\u0110\u01A1n gi\xE1: ", /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("strong", {
                  children: [formatNumber(this.state.product[PRODUCT_PRICE_REAL]), "\xA0VN\u0110"]
                })]
              }), this.state.product[PRODUCT_STATUS] == PRODUCT_STATUS_CONHANG ? /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("strong", {
                style: {
                  color: 'green'
                },
                children: "C\xF2n h\xE0ng"
              }) : /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("strong", {
                style: {
                  color: 'red'
                },
                children: "H\u1EBFt h\xE0ng"
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                className: "box_flex",
                style: {
                  margin: '5px 0px'
                },
                children: ["H\xE3ng s\u1EA3n xu\u1EA5t:\xA0", venderImg == '' ? '' : /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("img", {
                  style: {
                    height: 20
                  },
                  src: venderImg
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("b", {
                  children: ["\xA0", venderName]
                })]
              }), productPromotion, /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                style: {
                  marginTop: 10
                },
                children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("strong", {
                  children: "S\u1ED1 l\u01B0\u1EE3ng "
                })
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                className: "box_flex",
                children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  className: "button",
                  style: {
                    background: '#ccc',
                    padding: 5,
                    borderRadius: 5,
                    fontWeight: 'bold',
                    color: 'white',
                    width: 30,
                    textAlign: "center"
                  },
                  onClick: function onClick() {
                    if (_this5.state.quantity > 1) _this5.setState({
                      quantity: Number(_this5.state.quantity) - 1
                    });
                  },
                  children: "-"
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("input", {
                  className: "input_item_input",
                  style: {
                    width: 50,
                    margin: '0px 5px'
                  },
                  type: "number",
                  min: "0",
                  value: this.state.quantity,
                  onChange: function onChange(e) {
                    return _this5.setState({
                      quantity: e.target.value
                    });
                  }
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  className: "button",
                  style: {
                    background: '#ccc',
                    padding: 5,
                    borderRadius: 5,
                    fontWeight: 'bold',
                    color: 'white',
                    width: 30,
                    textAlign: "center"
                  },
                  onClick: function onClick() {
                    _this5.setState({
                      quantity: Number(_this5.state.quantity) + 1
                    });
                  },
                  children: "+"
                })]
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                style: {
                  marginTop: 10
                },
                children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("strong", {
                  children: "Thanh To\xE1n"
                })
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                className: "box_flex",
                children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                  style: {
                    color: 'gray',
                    fontWeight: 'bold',
                    fontSize: 'medium',
                    display: this.state.voucher == 0 ? 'none' : 'block',
                    textDecoration: 'line-through'
                  },
                  children: [formatNumber(Number(this.state.product[PRODUCT_PRICE_REAL]) * Number(this.state.quantity)), "\xA0VN\u0110"]
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                  style: {
                    color: this.state.voucher == 0 ? 'red' : 'green',
                    fontWeight: 'bold',
                    fontSize: 'large',
                    marginLeft: 15
                  },
                  children: [formatNumber(Number(this.state.product[PRODUCT_PRICE_REAL]) * Number(this.state.quantity) - Number(this.state.voucher)), "\xA0VN\u0110"]
                })]
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
                className: "box_flex",
                children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)(_components_user_InputVoucherOption__WEBPACK_IMPORTED_MODULE_3__.default, {
                  onApply: function onApply(voucher) {
                    _this5.setState({
                      voucher: voucher[VOUCHER_VALUE]
                    });
                  },
                  className: "input_item_input",
                  placeholder: "M\xE3 Gi\u1EA3m Gi\xE1",
                  option: this.state.vouchers,
                  ref: function ref(c) {
                    return _this5.voucherInput = c;
                  }
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                  className: "button btn btn-danger",
                  onClick: function onClick() {
                    _this5.order();
                  },
                  children: "\u0110\u1EB7t H\xE0ng"
                })]
              }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
                style: {
                  marginTop: 10
                },
                children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("textarea", {
                  className: "input_item_input",
                  style: {
                    width: '100%'
                  },
                  placeholder: "Ghi ch\xFA c\u1EE7a b\u1EA1n",
                  value: this.state.note,
                  onChange: function onChange(e) {
                    return _this5.setState({
                      note: e.target.value
                    });
                  }
                })
              })]
            })
          })]
        }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
          className: "box_padding",
          children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
            className: "box_flex title",
            children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("i", {
              className: "fa fa-cog"
            }), "\xA0", /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("strong", {
              children: "Th\xF4ng s\u1ED1 k\u1EF9 thu\u1EADt:"
            })]
          }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("table", {
            className: "table table-bordered table-striped",
            children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("thead", {
              children: /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("tr", {
                children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("th", {
                  children: "STT"
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("th", {
                  style: {
                    whiteSpace: 'nowrap'
                  },
                  children: "T\xEAn Tham s\u1ED1"
                }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("th", {
                  children: "Gi\xE1 tr\u1ECB"
                })]
              })
            }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("tbody", {
              children: this.state.product[SPECIFICATIONS_TABLE].map(function (item, key) {
                return /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("tr", {
                  children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("td", {
                    children: key + 1
                  }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("td", {
                    children: item[SPECT_NAME]
                  }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("td", {
                    children: [item[SPECT_VALUE], "\xA0", item[SPECT_UNIT]]
                  })]
                }, key);
              })
            })]
          })]
        }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
          className: "box_padding",
          children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsxs)("div", {
            className: "box_flex title",
            children: [/*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("i", {
              className: "fa fa-book"
            }), "\xA0", /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("strong", {
              children: "M\xF4 t\u1EA3 s\u1EA3n ph\u1EA9m"
            })]
          }), /*#__PURE__*/(0,react_jsx_runtime__WEBPACK_IMPORTED_MODULE_0__.jsx)("div", {
            className: "ck-content",
            dangerouslySetInnerHTML: {
              __html: output_secure(get(this.state.product[PRODUCT_DESCRIPTION], ''))
            }
          })]
        })]
      });
    }
  }]);

  return PagesHome;
}(react__WEBPACK_IMPORTED_MODULE_1__.Component);

/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = ((0,react_router_dom__WEBPACK_IMPORTED_MODULE_4__.default)(PagesHome));

/***/ }),

/***/ "./node_modules/css-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[1]!./node_modules/postcss-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[2]!./node_modules/sass-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[3]!./node_modules/sass-loader/dist/cjs.js!./resources/simulation/components/user/css/responsive.scss":
/*!***********************************************************************************************************************************************************************************************************************************************************************************************************************************************!*\
  !*** ./node_modules/css-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[1]!./node_modules/postcss-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[2]!./node_modules/sass-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[3]!./node_modules/sass-loader/dist/cjs.js!./resources/simulation/components/user/css/responsive.scss ***!
  \***********************************************************************************************************************************************************************************************************************************************************************************************************************************************/
/***/ ((module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var _node_modules_css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! ../../../../../node_modules/css-loader/dist/runtime/api.js */ "./node_modules/css-loader/dist/runtime/api.js");
/* harmony import */ var _node_modules_css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_node_modules_css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_0__);
// Imports

var ___CSS_LOADER_EXPORT___ = _node_modules_css_loader_dist_runtime_api_js__WEBPACK_IMPORTED_MODULE_0___default()(function(i){return i[1]});
// Module
___CSS_LOADER_EXPORT___.push([module.id, "@media only screen and (min-width: 768px) {\n  #saleBanner .carousel-item {\n    width: 100%;\n    height: 300px;\n    font-size: 32px;\n    background-repeat: no-repeat;\n    background-size: cover;\n    background-position: center;\n  }\n\n  .product_type_item {\n    height: 150px;\n    width: 150px;\n  }\n\n  .product_type_item img {\n    width: 80%;\n  }\n\n  .user_menu {\n    height: 50px;\n  }\n\n  .main {\n    margin-bottom: 50px;\n  }\n\n  .product_list {\n    display: flex;\n    flex-wrap: wrap;\n  }\n\n  .product_list .product_item {\n    width: 50%;\n  }\n}\n@media only screen and (max-width: 768px) {\n  #saleBanner .carousel-item {\n    width: 100%;\n    height: 100px;\n    background-repeat: no-repeat;\n    background-size: cover;\n    background-position: center;\n  }\n\n  .carousel-indicators {\n    margin-bottom: 0px;\n    bottom: 5px;\n  }\n\n  .product_type_item {\n    height: 100px;\n    max-width: 150px;\n    min-width: 100px;\n    width: 33%;\n  }\n\n  .user_menu {\n    height: 40px;\n  }\n\n  .main {\n    margin-bottom: 40px;\n  }\n}\n.product_types_frame {\n  display: flex;\n  flex-wrap: wrap;\n  justify-content: space-between;\n  margin-top: 7px;\n}\n\n.product_type_item {\n  margin: 0px;\n  display: flex;\n  flex-direction: column;\n  align-items: unset;\n  text-align: center;\n  padding: 15px;\n}\n\n.product_type_item .product_type_image {\n  flex-grow: 1;\n  background-size: contain;\n  background-repeat: no-repeat;\n  background-position: center;\n  margin-bottom: 7px;\n  border-radius: 5px;\n}\n\n.product_type_item .product_type_title {\n  color: gray;\n  font-weight: bold;\n}\n\n.user_menu {\n  position: fixed;\n  left: 0px;\n  right: 0px;\n  z-index: 1;\n  bottom: 0;\n  background: #eee;\n  display: flex;\n  justify-content: space-around;\n}\n\n.user_menu .button {\n  flex-grow: 1;\n  margin: 0px;\n  justify-content: center;\n  border-left: solid thin #ccc;\n  position: relative;\n}\n\n.user_menu .button.active {\n  background: #FF9800;\n  color: white;\n  font-weight: bold;\n}\n\n.user_menu .button .quantity {\n  position: absolute;\n  right: 5px;\n  top: 5px;\n  padding: 0px 3px;\n  border-radius: 5px;\n  font-size: 10px;\n  border: solid thin white;\n  color: white;\n  text-align: center;\n  background: #FF5722;\n}\n\n.product_list .product_item {\n  padding: 5px;\n  color: gray;\n  position: relative;\n}\n\n.product_list .product_item .product_item_image {\n  width: 60px;\n  height: 60px;\n}\n\n.product_list .product_item .product_item_image img {\n  width: 100%;\n  height: 100%;\n  -o-object-fit: contain;\n     object-fit: contain;\n}\n\n.product_list .product_item .product_item_name {\n  font-size: medium;\n}\n\n.product_page .product_page_image_active {\n  width: 100%;\n  text-align: center;\n  height: 200px;\n  align-items: center;\n  padding: 10px;\n}\n\n.product_page .product_page_image_child {\n  width: 50px;\n  height: 50px;\n  margin: 5px;\n  padding: 2px;\n  margin-bottom: 15px;\n}\n\n.product_page .product_page_image_child.active {\n  border: solid thin orange;\n}\n\n.product_page .product_page_image_frame {\n  border-radius: 5px;\n  border: solid thin darkgray;\n}\n\n.product_page .product_page_image_frame .title {\n  padding: 5px 10px;\n  background: orange;\n  color: white;\n}\n\n.product_page .product_item_name {\n  font-size: medium;\n  color: orange;\n}\n\n.image {\n  width: unset !important;\n  height: unset !important;\n}", ""]);
// Exports
/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (___CSS_LOADER_EXPORT___);


/***/ }),

/***/ "./node_modules/react-router-dom/es/withRouter.js":
/*!********************************************************!*\
  !*** ./node_modules/react-router-dom/es/withRouter.js ***!
  \********************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var react_router_es_withRouter__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react-router/es/withRouter */ "./node_modules/react-router-dom/node_modules/react-router/es/withRouter.js");
// Written in this round about way for babel-transform-imports


/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (react_router_es_withRouter__WEBPACK_IMPORTED_MODULE_0__.default);

/***/ }),

/***/ "./node_modules/react-router-dom/node_modules/hoist-non-react-statics/dist/hoist-non-react-statics.cjs.js":
/*!****************************************************************************************************************!*\
  !*** ./node_modules/react-router-dom/node_modules/hoist-non-react-statics/dist/hoist-non-react-statics.cjs.js ***!
  \****************************************************************************************************************/
/***/ ((module) => {



/**
 * Copyright 2015, Yahoo! Inc.
 * Copyrights licensed under the New BSD License. See the accompanying LICENSE file for terms.
 */
var REACT_STATICS = {
    childContextTypes: true,
    contextTypes: true,
    defaultProps: true,
    displayName: true,
    getDefaultProps: true,
    getDerivedStateFromProps: true,
    mixins: true,
    propTypes: true,
    type: true
};

var KNOWN_STATICS = {
    name: true,
    length: true,
    prototype: true,
    caller: true,
    callee: true,
    arguments: true,
    arity: true
};

var defineProperty = Object.defineProperty;
var getOwnPropertyNames = Object.getOwnPropertyNames;
var getOwnPropertySymbols = Object.getOwnPropertySymbols;
var getOwnPropertyDescriptor = Object.getOwnPropertyDescriptor;
var getPrototypeOf = Object.getPrototypeOf;
var objectPrototype = getPrototypeOf && getPrototypeOf(Object);

function hoistNonReactStatics(targetComponent, sourceComponent, blacklist) {
    if (typeof sourceComponent !== 'string') { // don't hoist over string (html) components

        if (objectPrototype) {
            var inheritedComponent = getPrototypeOf(sourceComponent);
            if (inheritedComponent && inheritedComponent !== objectPrototype) {
                hoistNonReactStatics(targetComponent, inheritedComponent, blacklist);
            }
        }

        var keys = getOwnPropertyNames(sourceComponent);

        if (getOwnPropertySymbols) {
            keys = keys.concat(getOwnPropertySymbols(sourceComponent));
        }

        for (var i = 0; i < keys.length; ++i) {
            var key = keys[i];
            if (!REACT_STATICS[key] && !KNOWN_STATICS[key] && (!blacklist || !blacklist[key])) {
                var descriptor = getOwnPropertyDescriptor(sourceComponent, key);
                try { // Avoid failures from read-only properties
                    defineProperty(targetComponent, key, descriptor);
                } catch (e) {}
            }
        }

        return targetComponent;
    }

    return targetComponent;
}

module.exports = hoistNonReactStatics;


/***/ }),

/***/ "./node_modules/react-router-dom/node_modules/react-router/es/withRouter.js":
/*!**********************************************************************************!*\
  !*** ./node_modules/react-router-dom/node_modules/react-router/es/withRouter.js ***!
  \**********************************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var react__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! react */ "./node_modules/react/index.js");
/* harmony import */ var prop_types__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! prop-types */ "./node_modules/prop-types/index.js");
/* harmony import */ var prop_types__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(prop_types__WEBPACK_IMPORTED_MODULE_1__);
/* harmony import */ var hoist_non_react_statics__WEBPACK_IMPORTED_MODULE_2__ = __webpack_require__(/*! hoist-non-react-statics */ "./node_modules/react-router-dom/node_modules/hoist-non-react-statics/dist/hoist-non-react-statics.cjs.js");
/* harmony import */ var hoist_non_react_statics__WEBPACK_IMPORTED_MODULE_2___default = /*#__PURE__*/__webpack_require__.n(hoist_non_react_statics__WEBPACK_IMPORTED_MODULE_2__);
/* harmony import */ var _Route__WEBPACK_IMPORTED_MODULE_3__ = __webpack_require__(/*! ./Route */ "./node_modules/react-router-dom/node_modules/react-router/es/Route.js");
var _extends = Object.assign || function (target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i]; for (var key in source) { if (Object.prototype.hasOwnProperty.call(source, key)) { target[key] = source[key]; } } } return target; };

function _objectWithoutProperties(obj, keys) { var target = {}; for (var i in obj) { if (keys.indexOf(i) >= 0) continue; if (!Object.prototype.hasOwnProperty.call(obj, i)) continue; target[i] = obj[i]; } return target; }






/**
 * A public higher-order component to access the imperative API
 */
var withRouter = function withRouter(Component) {
  var C = function C(props) {
    var wrappedComponentRef = props.wrappedComponentRef,
        remainingProps = _objectWithoutProperties(props, ["wrappedComponentRef"]);

    return react__WEBPACK_IMPORTED_MODULE_0__.createElement(_Route__WEBPACK_IMPORTED_MODULE_3__.default, {
      children: function children(routeComponentProps) {
        return react__WEBPACK_IMPORTED_MODULE_0__.createElement(Component, _extends({}, remainingProps, routeComponentProps, {
          ref: wrappedComponentRef
        }));
      }
    });
  };

  C.displayName = "withRouter(" + (Component.displayName || Component.name) + ")";
  C.WrappedComponent = Component;
  C.propTypes = {
    wrappedComponentRef: (prop_types__WEBPACK_IMPORTED_MODULE_1___default().func)
  };

  return hoist_non_react_statics__WEBPACK_IMPORTED_MODULE_2___default()(C, Component);
};

/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (withRouter);

/***/ }),

/***/ "./resources/simulation/components/user/css/responsive.scss":
/*!******************************************************************!*\
  !*** ./resources/simulation/components/user/css/responsive.scss ***!
  \******************************************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

__webpack_require__.r(__webpack_exports__);
/* harmony export */ __webpack_require__.d(__webpack_exports__, {
/* harmony export */   "default": () => (__WEBPACK_DEFAULT_EXPORT__)
/* harmony export */ });
/* harmony import */ var _node_modules_style_loader_dist_runtime_injectStylesIntoStyleTag_js__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! !../../../../../node_modules/style-loader/dist/runtime/injectStylesIntoStyleTag.js */ "./node_modules/style-loader/dist/runtime/injectStylesIntoStyleTag.js");
/* harmony import */ var _node_modules_style_loader_dist_runtime_injectStylesIntoStyleTag_js__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(_node_modules_style_loader_dist_runtime_injectStylesIntoStyleTag_js__WEBPACK_IMPORTED_MODULE_0__);
/* harmony import */ var _node_modules_css_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_1_node_modules_postcss_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_2_node_modules_sass_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_3_node_modules_sass_loader_dist_cjs_js_responsive_scss__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! !!../../../../../node_modules/css-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[1]!../../../../../node_modules/postcss-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[2]!../../../../../node_modules/sass-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[3]!../../../../../node_modules/sass-loader/dist/cjs.js!./responsive.scss */ "./node_modules/css-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[1]!./node_modules/postcss-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[2]!./node_modules/sass-loader/dist/cjs.js??ruleSet[1].rules[6].oneOf[1].use[3]!./node_modules/sass-loader/dist/cjs.js!./resources/simulation/components/user/css/responsive.scss");

            

var options = {};

options.insert = "head";
options.singleton = false;

var update = _node_modules_style_loader_dist_runtime_injectStylesIntoStyleTag_js__WEBPACK_IMPORTED_MODULE_0___default()(_node_modules_css_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_1_node_modules_postcss_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_2_node_modules_sass_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_3_node_modules_sass_loader_dist_cjs_js_responsive_scss__WEBPACK_IMPORTED_MODULE_1__.default, options);



/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (_node_modules_css_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_1_node_modules_postcss_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_2_node_modules_sass_loader_dist_cjs_js_ruleSet_1_rules_6_oneOf_1_use_3_node_modules_sass_loader_dist_cjs_js_responsive_scss__WEBPACK_IMPORTED_MODULE_1__.default.locals || {});

/***/ })

}]);